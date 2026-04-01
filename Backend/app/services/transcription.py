import time
import subprocess
import os
import numpy as np
import imageio_ffmpeg

ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()



from app.schemas.journalSchemas import Transcript, Sentence, WordToken
from app.config import settings


from app.logging_config import logger

class TranscriptionManager:

    def __init__(self):
        self.device = settings.DEVICE
        self.model_size = settings.WHISPER_MODEL
        self.compute_type = settings.COMPUTE_TYPE
        self.sample_rate = getattr(settings, "SAMPLE_RATE", 16000) or 16000
        self.language = settings.LANGUAGE
        self.whisperx = self._load_whisperx()

        logger.info(f"Loading WhisperX ({self.model_size}) on {self.device}...")
        self.asr_model = self.whisperx.load_model(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
            language=self.language,
        )

        self.alignment_model, self.align_metadata = self.whisperx.load_align_model(
            language_code=self.language,
            device=self.device,
        )


    def transcribe(self, recording):
        """
        Transcribes an audio file (Recording) into a Transcript object.
        Performs automatic alignment and per-word timing.
        """

        audio = self._load_audio_ffmpeg(recording.path, sr=self.sample_rate)
    
        start_time = time.time()
        result = self.asr_model.transcribe(audio)
        logger.info(f"Raw transcription done in {time.time() - start_time:.2f}s")
    
        if result.get("language") and result["language"] != self.align_metadata.get("language"):
            self.alignment_model, self.align_metadata = self.whisperx.load_align_model(
                language_code=result["language"],
                device=self.device,
            )
    
        result_aligned = self.whisperx.align(
            transcript=result["segments"],
            model=self.alignment_model,
            align_model_metadata=self.align_metadata,
            audio=audio,
            device=self.device,
            return_char_alignments=False,
        )
    
        text = " ".join(
            [(seg.get("text", "") or "").strip() for seg in result_aligned.get("segments", [])]
        ).strip()
    
        words = self._extract_words(result_aligned)
        sentences = self._extract_sentences(result_aligned, recording.id)
    
        return Transcript(
            recording_id=recording.id,
            text=text,
            words=words,
            sentences=sentences,
            source="whisperx",
        )

    @staticmethod
    def _load_whisperx():
        try:
            import whisperx

            return whisperx
        except Exception as exc:
            detail = str(exc)
            if "_libsvm" in detail and "blocked" in detail.lower():
                message = (
                    "Transcription is unavailable: Windows Application Control blocked "
                    "scikit-learn's _libsvm binary dependency used by WhisperX/pyannote. "
                    "Ask IT to allow this binary or use a transcription path without WhisperX."
                )
            else:
                message = f"Transcription dependencies failed to load: {detail}"

            logger.exception(message)
            raise NotImplementedError(message) from exc


    @staticmethod
    def _load_audio_ffmpeg(path: str, sr: int = 16000) -> np.ndarray:
        """
        Loads audio via ffmpeg and returns a float32 mono waveform in [-1, 1].
        """
        if not os.path.exists(path):
            logger.error(f"Audio file not found: {path}")
            raise RuntimeError(f"Audio file not found: {path}")
        

        cmd = [
            ffmpeg_exe,
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
            logger.error("FFmpeg command not found. Is it in PATH?")
            raise RuntimeError("FFmpeg command not found. Is it in PATH?")

        if p.returncode != 0:
            stderr = (p.stderr or b"").decode("utf-8", errors="replace")
            raise RuntimeError(f"ffmpeg failed ({p.returncode}): {stderr[:1200]}")

        raw = p.stdout or b""
        if not raw:
            raise RuntimeError("ffmpeg returned empty audio buffer.")

        audio = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
        if audio.size == 0:
            raise RuntimeError("Audio decode produced empty numpy array.")

        return audio

    @staticmethod
    def _extract_words(result_aligned):
        out = []
        for seg in result_aligned.get("segments", []) or []:
            for w in seg.get("words", []) or []:
                out.append(
                    WordToken(
                        word=(w.get("word", "") or "").strip(),
                        start_s=w.get("start"),
                        end_s=w.get("end"),
                        prob=w.get("score"),
                    )
                )
        return out
    
    @staticmethod
    def _extract_sentences(result_aligned, recording_id: str):
        sentences = []
        for i, seg in enumerate(result_aligned.get("segments", []) or []):
            sentences.append(
                Sentence(
                    id=i,
                    start_s=seg.get("start"),
                    end_s=seg.get("end"),
                    text=(seg.get("text", "") or "").strip(),
                    meta={"recording_id": recording_id},
                )
            )
        return sentences