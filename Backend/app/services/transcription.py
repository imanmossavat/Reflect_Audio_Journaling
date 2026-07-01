import platform
import subprocess
import os
import time
import numpy as np
import imageio_ffmpeg
from datetime import datetime, timezone

ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

from app.schemas.journalSchemas import Transcript, Sentence, WordToken
from app.config import settings
from app.logging_config import logger
from app.services.settings_service import device_available


class TranscriptionManager:

    def __init__(self):
        self.device = settings.DEVICE
        if not device_available(self.device):
            # Guards against a stale settings.json (e.g. copied from another
            # machine, or written before torch was reinstalled without CUDA
            # support) claiming a device that no longer exists here.
            logger.warning(
                f"[INIT] Configured device={self.device!r} is not available on this "
                "machine; falling back to cpu"
            )
            self.device = "cpu"
        self.model_size = settings.WHISPER_MODEL
        self.compute_type = "float16" if self.device in {"cuda", "mps"} else "int8"
        self.sample_rate = getattr(settings, "SAMPLE_RATE", 16000) or 16000
        self.language = settings.LANGUAGE

        logger.info(f"[INIT] Loading WhisperX model={self.model_size} device={self.device}")

        self.whisperx = self._load_whisperx()

        logger.info("[INIT] Loading ASR model...")
        if self.device == "mps":
            # CTranslate2 (faster-whisper) does not support MPS.
            # Use openai-whisper (PyTorch) which supports mps/cuda/cpu uniformly.
            self._openai_model = self._load_openai_whisper()
        else:
            self.asr_model = self.whisperx.load_model(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                language=self.language,
            )

        logger.info("[INIT] Loading alignment model...")
        self.alignment_model, self.align_metadata = self.whisperx.load_align_model(
            language_code=self.language,
            device=self.device,
        )

        logger.info("[INIT] TranscriptionManager ready")

    def transcribe(self, recording):
        logger.info(f"[TRANSCRIBE] Start recording_id={recording.id} path={recording.path}")

        started_at = datetime.now(timezone.utc)
        start_perf = time.perf_counter()

        audio = self._load_audio_ffmpeg(recording.path, sr=self.sample_rate)

        logger.info(f"[TRANSCRIBE] Audio loaded shape={audio.shape} sr={self.sample_rate}")

        logger.info("[WHISPER] Running ASR transcription")
        if self.device == "mps":
            result = self._transcribe_openai_whisper(audio)
        else:
            result = self.asr_model.transcribe(audio)

        logger.info(f"[WHISPER] Done language={result.get('language')} segments={len(result.get('segments', []))}")

        if result.get("language") and result["language"] != self.align_metadata.get("language"):
            logger.info(f"[ALIGN] Switching alignment model to {result['language']}")
            self.alignment_model, self.align_metadata = self.whisperx.load_align_model(
                language_code=result["language"],
                device=self.device,
            )

        logger.info("[ALIGN] Running alignment")
        result_aligned = self.whisperx.align(
            transcript=result["segments"],
            model=self.alignment_model,
            align_model_metadata=self.align_metadata,
            audio=audio,
            device=self.device,
            return_char_alignments=False,
        )

        logger.info("[ALIGN] Completed")

        text = " ".join(
            [(seg.get("text", "") or "").strip() for seg in result_aligned.get("segments", [])]
        ).strip()

        words = self._extract_words(result_aligned)
        sentences = self._extract_sentences(result_aligned, recording.id)

        duration_s = round(time.perf_counter() - start_perf, 3)
        finished_at = datetime.now(timezone.utc)

        logger.info(
            f"[TRANSCRIBE] Finished recording_id={recording.id} "
            f"text_len={len(text)} words={len(words)} sentences={len(sentences)} duration_s={duration_s}"
        )

        meta = {
            "model": self.model_size,
            "engine": "openai-whisper" if self.device == "mps" else "whisperx",
            "device": self.device,
            "compute_type": self.compute_type,
            "language_configured": self.language,
            "language_detected": result.get("language"),
            "os": platform.platform(),
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_s": duration_s,
        }

        return Transcript(
            recording_id=recording.id,
            text=text,
            words=words,
            sentences=sentences,
            source="whisperx",
            meta=meta,
        )

    def _load_openai_whisper(self):
        # Whisper's decoder builds sparse attention tensors. PyTorch's SparseMPS backend
        # has no kernel for _sparse_coo_tensor_with_dims_and_tensors, so the decode step
        # crashes on MPS regardless of PYTORCH_ENABLE_MPS_FALLBACK (that flag only covers
        # the dense MPS key, not SparseMPS). Load ASR on CPU; the alignment step still
        # runs on MPS via WhisperX's wav2vec2 model.
        asr_device = "cpu" if self.device == "mps" else self.device
        logger.info(f"[INIT] Loading openai-whisper model={self.model_size} asr_device={asr_device} (system_device={self.device})")
        try:
            import whisper as _ow
        except ImportError:
            raise RuntimeError(
                "openai-whisper is required for MPS transcription. "
                "Run: uv add openai-whisper"
            )
        return _ow.load_model(self.model_size, device=asr_device)

    def _transcribe_openai_whisper(self, audio: np.ndarray) -> dict:
        # ASR runs on CPU when system device is MPS (see _load_openai_whisper).
        asr_device = "cpu" if self.device == "mps" else self.device
        result = self._openai_model.transcribe(
            audio,
            language=self.language or None,
            word_timestamps=True,
            verbose=False,
            fp16=(asr_device == "cuda"),
        )
        return result

    @staticmethod
    def _load_whisperx():
        try:
            logger.info("[WHISPERX] Importing whisperx")
            import whisperx
            logger.info("[WHISPERX] Import successful")
            return whisperx

        except Exception as exc:
            logger.exception(f"[WHISPERX] Failed to load: {exc}")
            raise

    @staticmethod
    def _load_audio_ffmpeg(path: str, sr: int = 16000) -> np.ndarray:
        logger.info(f"[FFMPEG] Loading audio path={path} sr={sr}")

        if not os.path.exists(path):
            logger.error(f"[FFMPEG] File not found: {path}")
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

        logger.info(f"[FFMPEG] Running command")

        try:
            p = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
        except FileNotFoundError:
            logger.exception("[FFMPEG] Binary not found in PATH")
            raise RuntimeError("FFmpeg command not found. Is it in PATH?")

        if p.returncode != 0:
            stderr = (p.stderr or b"").decode("utf-8", errors="replace")
            logger.error(f"[FFMPEG] Failed rc={p.returncode} err={stderr[:1000]}")
            raise RuntimeError(f"ffmpeg failed ({p.returncode}): {stderr[:1200]}")

        raw = p.stdout or b""
        if not raw:
            logger.error("[FFMPEG] Empty output buffer")
            raise RuntimeError("ffmpeg returned empty audio buffer.")

        audio = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0

        logger.info(f"[FFMPEG] Decoded samples={audio.shape[0]}")

        if audio.size == 0:
            logger.error("[FFMPEG] Empty numpy array after decode")
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