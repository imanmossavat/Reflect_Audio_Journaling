import time
import subprocess
import numpy as np
import whisperx

from app.domain.models import Transcript
from app.core.config import settings

DEVICE = "cpu"
BATCH_SIZE = 16
COMPUTE_TYPE = "float32"

class TranscriptionManager:
    """
    Handles transcription and word alignment using WhisperX.
    """

    def __init__(self):
        self.device = settings.DEVICE
        self.model_size = settings.WHISPER_MODEL
        self.compute_type = settings.COMPUTE_TYPE
        self.sample_rate = settings.SAMPLE_RATE

        print(f"[TranscriptionManager] Loading WhisperX ( {self.model_size} ) on {self.device}...")
        self.asr_model = whisperx.load_model(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
            language=settings.LANGUAGE
        )

        self.alignment_model, self.align_metadata = whisperx.load_align_model(
            language_code=settings.LANGUAGE,
            device=self.device
        )

    # ---------------- PUBLIC METHODS ---------------- #

    def transcribe(self, recording):
        """
        Transcribes an audio file (Recording) into a Transcript object.
        Performs automatic alignment and per-word timing.
        """
        audio = self._load_audio_ffmpeg(recording.path)
        sr = 16000

        start_time = time.time()
        result = self.asr_model.transcribe(audio)
        print(f"[TranscriptionManager] Raw transcription done in {time.time() - start_time:.2f}s")

        # Adjust language if needed
        if result["language"] != self.align_metadata["language"]:
            self.alignment_model, self.align_metadata = whisperx.load_align_model(
                language_code=result["language"], device=self.device
            )

        result_aligned = whisperx.align(
            transcript=result["segments"],
            model=self.alignment_model,
            align_model_metadata=self.align_metadata,
            audio=audio,
            device=self.device,
            return_char_alignments=False
        )

        words = self._extract_words(result_aligned)
        text = " ".join([seg.get("text", "") for seg in result_aligned["segments"]])

        return Transcript(recording_id=recording.id, text=text, words=words)

    # ---------------- HELPER METHODS ---------------- #

    @staticmethod
    def _load_audio_ffmpeg(path: str, sr: int = 16000) -> np.ndarray:
        cmd = ["ffmpeg", "-i", path, "-f", "s16le", "-ac", "1", "-ar", str(sr), "-"]
        try:
            out = subprocess.run(cmd, capture_output=True, check=True).stdout
            audio = np.frombuffer(out, np.int16).astype(np.float32) / 32768.0
            return audio
        except FileNotFoundError:
            raise RuntimeError("FFmpeg kon niet uitgevoerd worden. Staat het wel in PATH?")

    @staticmethod
    def _extract_words(result_aligned):
        segments_out = []
        for seg in result_aligned["segments"]:
            words = []
            if "words" in seg:
                for w in seg["words"]:
                    words.append({
                        "text": w.get("word", ""),
                        "start": w.get("start"),
                        "end": w.get("end")
                    })
            segments_out.append({
                "start": seg.get("start"),
                "end": seg.get("end"),
                "text": seg.get("text", ""),
                "words": words
            })
        return segments_out
