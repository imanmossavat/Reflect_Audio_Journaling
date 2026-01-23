# app/services/segmentation.py
from __future__ import annotations

import re
from typing import Dict, List, Sequence, Tuple

import numpy as np
import spacy
from sentence_transformers import SentenceTransformer
from sklearn.cluster import SpectralCoclustering
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.config import settings
from app.domain.models import Segment


class SegmentationManager:
    """
    Topic segmentation + labeling.
    Segmentation strategies: adaptive | spectral
    Labeling: noun-chunk candidates ranked by embedding similarity (fallback TF-IDF)
    """

    def __init__(self):
        self.model = SentenceTransformer(settings.SEGMENTATION_MODEL)

        self.strategy = settings.SEGMENTATION_STRATEGY  # adaptive | spectral

        self.similarity_method = settings.SEGMENTATION_SIMILARITY_METHOD  # std | percentile
        self.std_factor = settings.SEGMENTATION_STD_FACTOR
        self.min_size = settings.SEGMENTATION_MIN_SIZE
        self.percentile = settings.SEGMENTATION_PERCENTILE

        self.top_n = settings.SEGMENTATION_TOPIC_TOP_N

        # topic phrase extraction
        spacy_model = getattr(settings, "SEGMENTATION_SPACY_MODEL", "en_core_web_trf")
        self.nlp = spacy.load(spacy_model)

        self._bad_phrase = re.compile(r"^\W*$")
        self._stoplike = {
            "i", "you", "we", "they", "he", "she", "it", "me", "my", "your", "our",
            "this", "that", "these", "those", "something", "anything", "everything",
            "thing", "stuff", "people", "time", "day", "way", "lot",
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def segment(self, transcript, recording_id: str) -> List[Segment]:
        sentence_objs = getattr(transcript, "sentences", None)
        if not sentence_objs or len(sentence_objs) < 2:
            return [
                Segment(
                    recording_id=recording_id,
                    id=0,
                    start_s=0,
                    end_s=0,
                    label="short transcript",
                    sentence_ids=[],
                    text=getattr(transcript, "text", ""),
                )
            ]

        # normalize sentence access (dict or dataclass)
        def s_text(s): return s.text if hasattr(s, "text") else s["text"]
        def s_start(s): return s.start_s if hasattr(s, "start_s") else s.get("start_s")
        def s_end(s): return s.end_s if hasattr(s, "end_s") else s.get("end_s")
        def s_id(s): return s.id if hasattr(s, "id") else s.get("id")

        sentences = [str(s_text(s) or "").strip() for s in sentence_objs]
        embeddings = self.model.encode(sentences, convert_to_numpy=True)

        if self.strategy == "spectral":
            seg_ids, _, _ = self._spectral_segmentation(sentences)
        else:
            seg_ids, _ = self._adaptive_threshold_segmentation(
                embeddings,
                method=self.similarity_method,
                min_size=self.min_size,
                std_factor=self.std_factor,
                percentile=self.percentile,
            )

        topics = self._get_segment_topics(
            sentences=sentences,
            segments=seg_ids,
            sentence_embeddings=embeddings,
            top_n=self.top_n,
        )

        out: List[Segment] = []
        for seg_id in sorted(set(seg_ids)):
            idxs = [i for i, sid in enumerate(seg_ids) if sid == seg_id]
            if not idxs:
                continue

            first = sentence_objs[idxs[0]]
            last = sentence_objs[idxs[-1]]

            out.append(
                Segment(
                    recording_id=recording_id,
                    id=int(seg_id),
                    start_s=s_start(first),
                    end_s=s_end(last),
                    label=(topics.get(seg_id) or [f"Segment {seg_id}"])[0],
                    sentence_ids=[s_id(sentence_objs[i]) for i in idxs],
                    text=" ".join(sentences[i] for i in idxs).strip(),
                )
            )

        return out

    # ------------------------------------------------------------------
    # Segmentation strategies
    # ------------------------------------------------------------------

    def _spectral_segmentation(self, sentences: Sequence[str], n_topics: int = 3) -> Tuple[List[int], List[int], np.ndarray]:
        vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
        m = vectorizer.fit_transform(sentences).toarray()

        model = SpectralCoclustering(n_clusters=n_topics, random_state=42)
        model.fit(m)

        labels = model.row_labels_
        boundaries = [i for i in range(1, len(labels)) if labels[i] != labels[i - 1]]
        seg_ids = self._boundaries_to_segments(boundaries, len(sentences), min_size=1)
        return seg_ids, boundaries, labels

    @staticmethod
    def _boundaries_to_segments(boundaries: Sequence[int], n: int, min_size: int = 1) -> List[int]:
        seg_ids = [0] * n
        current = 0
        last = 0

        for b in boundaries:
            if b - last >= min_size:
                current += 1
                last = b
            for i in range(b, n):
                seg_ids[i] = current

        return seg_ids

    @staticmethod
    def _adaptive_threshold_segmentation(
        embeddings: np.ndarray,
        method: str = "std",
        min_size: int = 2,
        std_factor: float = 1.0,
        percentile: int = 20,
    ) -> Tuple[List[int], float]:
        n = embeddings.shape[0]
        if n < 2:
            return [0] * n, 0.0

        sims = np.array([
            cosine_similarity(embeddings[i - 1].reshape(1, -1), embeddings[i].reshape(1, -1))[0][0]
            for i in range(1, n)
        ])

        if method == "std":
            threshold = float(sims.mean() - std_factor * sims.std())
        elif method == "percentile":
            threshold = float(np.percentile(sims, percentile))
        else:
            raise ValueError("method must be 'std' or 'percentile'")

        seg_ids = [0]
        cur = 0
        last_boundary = 0

        for i in range(1, n):
            if sims[i - 1] < threshold and (i - last_boundary) >= min_size:
                cur += 1
                last_boundary = i
            seg_ids.append(cur)

        return seg_ids, threshold

    # ------------------------------------------------------------------
    # Topic labels
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_phrase(p: str) -> str:
        p = (p or "").strip()
        p = re.sub(r"\s+", " ", p)
        return p

    def _phrase_ok(self, p: str) -> bool:
        if not p:
            return False
        if self._bad_phrase.match(p):
            return False

        toks = p.lower().split()
        if len(toks) == 0 or len(toks) > 4:
            return False
        if len(p) < 3:
            return False
        if all(t in self._stoplike for t in toks):
            return False
        return True

    @staticmethod
    def _fallback_tfidf_phrase(sentences: Sequence[str], segments: Sequence[int], top_n: int = 1) -> Dict[int, List[str]]:
        out: Dict[int, List[str]] = {}
        for seg_id in sorted(set(segments)):
            seg_text = " ".join(s for s, sid in zip(sentences, segments) if sid == seg_id).strip()
            if not seg_text:
                out[seg_id] = ["[no topic]"]
                continue

            vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=3000)
            X = vectorizer.fit_transform([seg_text])
            feats = np.array(vectorizer.get_feature_names_out())
            scores = X.toarray()[0]

            idx = scores.argsort()[::-1][:top_n]
            out[seg_id] = feats[idx].tolist() if len(idx) else ["[no topic]"]

        return out

    def _get_segment_topics(
        self,
        sentences: Sequence[str],
        segments: Sequence[int],
        sentence_embeddings: np.ndarray,
        top_n: int = 1,
    ) -> Dict[int, List[str]]:
        out: Dict[int, List[str]] = {}

        for seg_id in sorted(set(segments)):
            idxs = [i for i, sid in enumerate(segments) if sid == seg_id]
            if not idxs:
                continue

            seg_text = " ".join(sentences[i] for i in idxs).strip()
            if not seg_text:
                out[seg_id] = ["[no topic]"]
                continue

            seg_emb = sentence_embeddings[idxs].mean(axis=0, keepdims=True)

            doc = self.nlp(seg_text)
            candidates: List[str] = []
            for chunk in doc.noun_chunks:
                p = self._clean_phrase(chunk.text)
                if self._phrase_ok(p):
                    candidates.append(p)

            # dedupe (case-insensitive)
            seen = set()
            candidates = [c for c in candidates if not (c.lower() in seen or seen.add(c.lower()))]

            if not candidates:
                out.update(self._fallback_tfidf_phrase(sentences, segments, top_n=top_n))
                continue

            cand_emb = self.model.encode(candidates, convert_to_numpy=True)
            sims = cosine_similarity(seg_emb, cand_emb)[0]
            best = sims.argsort()[::-1][:top_n]
            out[seg_id] = [candidates[i] for i in best]

        return out