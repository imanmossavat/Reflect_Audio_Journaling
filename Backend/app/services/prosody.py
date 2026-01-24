import numpy as np
import librosa
from typing import List

from app.domain.models import Transcript, ProsodyFeatures, Sentence
from app.core.config import settings


class ProsodyManager:
    """
    Computes low-level prosodic features from audio.
    No interpretation. No emotion labels. Just signals.
    """
    def __init__(self):
        self.sample_rate = getattr(settings, "SAMPLE_RATE", 16000) or 16000
        self.silence_threshold = getattr(settings, "SILENCE_THRESHOLD", 0.01)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_sentences(
            self,
            transcript: Transcript,
            audio: np.ndarray,
    ) -> List[ProsodyFeatures]:
        """
        Compute prosody features per sentence.
        """
        if not transcript.sentences:
            return []

        features = []

        for s in transcript.sentences:
            pf = self._analyze_sentence(s, audio)
            if pf:
                features.append(pf)

        return features

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _analyze_sentence(
            self,
            sentence: Sentence,
            audio: np.ndarray,
    ) -> ProsodyFeatures | None:

        if sentence.start_s is None or sentence.end_s is None:
            return None

        start = int(sentence.start_s * self.sample_rate)
        end = int(sentence.end_s * self.sample_rate)

        if end <= start or end > len(audio):
            return None

        segment = audio[start:end]
        if segment.size == 0:
            return None

        # ---- RMS energy ----
        rms = librosa.feature.rms(y=segment)[0]
        rms_mean = float(np.mean(rms))
        rms_var = float(np.var(rms))

        # ---- speaking rate ----
        duration_s = sentence.end_s - sentence.start_s
        word_count = len(sentence.text.split()) if sentence.text else 0
        speaking_rate = (word_count / duration_s) * 60 if duration_s > 0 else None

        # ---- pause ratio ----
        silence = np.sum(np.abs(segment) < self.silence_threshold)
        pause_ratio = silence / segment.size if segment.size > 0 else None

        return ProsodyFeatures(
            recording_id=sentence.meta.get("recording_id") if sentence.meta else None,
            sentence_id=sentence.id,
            rms_mean=rms_mean,
            rms_var=rms_var,
            speaking_rate_wpm=speaking_rate,
            pause_ratio=pause_ratio,
        )
