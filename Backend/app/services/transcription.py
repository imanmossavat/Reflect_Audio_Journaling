import time
import subprocess
import os
import numpy as np
import whisperx

from app.domain.models import Transcript
from app.core.config import settings


class TranscriptionManager:
    """
    Handles transcription and word alignment using WhisperX.
    """

    def __init__(self):
        self.device = settings.DEVICE
        self.model_size = settings.WHISPER_MODEL
        self.compute_type = settings.COMPUTE_TYPE
        self.sample_rate = getattr(settings, "SAMPLE_RATE", 16000) or 16000
        self.language = settings.LANGUAGE

        print(f"[TranscriptionManager] Loading WhisperX ({self.model_size}) on {self.device}...")
        self.asr_model = whisperx.load_model(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
            language=self.language,
        )

        self.alignment_model, self.align_metadata = whisperx.load_align_model(
            language_code=self.language,
            device=self.device,
        )

    # ---------------- PUBLIC METHODS ---------------- #

    def transcribe(self, recording):
        """
        Transcribes an audio file (Recording) into a Transcript object.
        Performs automatic alignment and per-word timing.
        """
        audio = self._load_audio_ffmpeg(recording.path, sr=self.sample_rate)

        start_time = time.time()
        result = self.asr_model.transcribe(audio)
        print(f"[TranscriptionManager] Raw transcription done in {time.time() - start_time:.2f}s")

        # Adjust language if needed
        if result.get("language") and result["language"] != self.align_metadata.get("language"):
            self.alignment_model, self.align_metadata = whisperx.load_align_model(
                language_code=result["language"],
                device=self.device,
            )

        result_aligned = whisperx.align(
            transcript=result["segments"],
            model=self.alignment_model,
            align_model_metadata=self.align_metadata,
            audio=audio,
            device=self.device,
            return_char_alignments=False,
        )

        words = self._extract_words(result_aligned)
        text = " ".join([seg.get("text", "") for seg in result_aligned.get("segments", [])]).strip()

        return Transcript(recording_id=recording.id, text=text, words=words)

    # ---------------- HELPER METHODS ---------------- #

    @staticmethod
    def _load_audio_ffmpeg(path: str, sr: int = 16000) -> np.ndarray:
        """
        Loads audio via ffmpeg and returns a float32 mono waveform in [-1, 1].
        IMPORTANT:
        - Must be binary (no text=True), otherwise Windows will try to decode bytes (cp1252) and explode.
        """
        if not os.path.exists(path):
            raise RuntimeError(f"Audio file not found: {path}")

        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            path,
            "-f",
            "s16le",
            "-ac",
            "1",
            "-ar",
            str(sr),
            "-",
        ]

        try:
            p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        except FileNotFoundError:
            raise RuntimeError("FFmpeg kon niet uitgevoerd worden. Staat het wel in PATH?")

        if p.returncode != 0:
            stderr = (p.stderr or b"").decode("utf-8", errors="replace")
            raise RuntimeError(f"ffmpeg failed ({p.returncode}): {stderr[:1200]}")

        raw = p.stdout or b""
        if len(raw) == 0:
            raise RuntimeError("ffmpeg returned empty audio buffer (no data).")

        # Convert PCM16 -> float32 [-1, 1]
        audio = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0

        if audio.size == 0:
            raise RuntimeError("Audio decode produced empty numpy array.")

        return audio

    @staticmethod
    def _extract_words(result_aligned):
        segments_out = []
        for seg in result_aligned.get("segments", []):
            words = []
            for w in seg.get("words", []) or []:
                words.append(
                    {
                        "text": w.get("word", ""),
                        "start": w.get("start"),
                        "end": w.get("end"),
                    }
                )
            segments_out.append(
                {
                    "start": seg.get("start"),
                    "end": seg.get("end"),
                    "text": seg.get("text", ""),
                    "words": words,
                }
            )
        return segments_out
