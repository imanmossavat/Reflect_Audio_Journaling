import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import SpectralCoclustering
from sentence_transformers import SentenceTransformer

from app.domain.models import Segment
from app.core.config import settings


class SegmentationManager:
    """
    Handles topic segmentation on transcripts using sentence embeddings.
    Works with Sentence objects OR dict-based sentences.
    """

    def __init__(self):
        self.model = SentenceTransformer(settings.SEGMENTATION_MODEL)

        # high-level strategy
        self.strategy = settings.SEGMENTATION_STRATEGY  # adaptive | spectral

        # adaptive parameters
        self.similarity_method = settings.SEGMENTATION_SIMILARITY_METHOD  # std | percentile
        self.std_factor = settings.SEGMENTATION_STD_FACTOR
        self.min_size = settings.SEGMENTATION_MIN_SIZE
        self.percentile = settings.SEGMENTATION_PERCENTILE

        self.top_n = settings.SEGMENTATION_TOPIC_TOP_N

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def segment(self, transcript, recording_id: str):
        """
        Segment a Transcript into topic-based segments.
        """

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

        # ---- normalize sentence access (dict or dataclass) ----
        def s_text(s): return s.text if hasattr(s, "text") else s["text"]
        def s_start(s): return s.start_s if hasattr(s, "start_s") else s.get("start_s")
        def s_end(s): return s.end_s if hasattr(s, "end_s") else s.get("end_s")
        def s_id(s): return s.id if hasattr(s, "id") else s.get("id")

        sentences = [s_text(s) for s in sentence_objs]

        # ---- embeddings ----
        embeddings = self.model.encode(sentences)

        # ---- segmentation strategy ----
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

        # ---- topic labels ----
        topics = self._get_segment_topics(sentences, seg_ids, top_n=self.top_n)

        # ---- build Segment objects ----
        segments = []
        for seg_id in sorted(set(seg_ids)):
            indices = [i for i, sid in enumerate(seg_ids) if sid == seg_id]
            if not indices:
                continue

            first = sentence_objs[indices[0]]
            last = sentence_objs[indices[-1]]

            segments.append(
                Segment(
                    recording_id=recording_id,
                    id=seg_id,
                    start_s=s_start(first),
                    end_s=s_end(last),
                    label=(topics.get(seg_id) or [f"Segment {seg_id}"])[0],
                    sentence_ids=[s_id(sentence_objs[i]) for i in indices],
                    text=" ".join(sentences[i] for i in indices),
                )
            )

        return segments

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _spectral_segmentation(self, sentences, n_topics=3):
        vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
        m = vectorizer.fit_transform(sentences).toarray()

        model = SpectralCoclustering(n_clusters=n_topics, random_state=42)
        model.fit(m)

        labels = model.row_labels_
        boundaries = [i for i in range(1, len(labels)) if labels[i] != labels[i - 1]]
        segments = self._boundaries_to_segments(boundaries, len(sentences))
        return segments, boundaries, labels

    @staticmethod
    def _boundaries_to_segments(boundaries, num_sentences, min_size=1):
        segments = [0] * num_sentences
        current = 0
        last_boundary = -1

        for b in boundaries:
            if b - last_boundary >= min_size:
                last_boundary = b
                current += 1
            segments[b:] = [current] * (num_sentences - b)

        return segments

    @staticmethod
    def _adaptive_threshold_segmentation(
            embeddings,
            method="std",
            min_size=2,
            std_factor=1.0,
            percentile=20,
    ):
        num_sentences = embeddings.shape[0]
        sims = np.array([
            cosine_similarity(
                embeddings[i - 1].reshape(1, -1),
                embeddings[i].reshape(1, -1),
            )[0][0]
            for i in range(1, num_sentences)
        ])

        if method == "std":
            threshold = sims.mean() - std_factor * sims.std()
        elif method == "percentile":
            threshold = np.percentile(sims, percentile)
        else:
            raise ValueError("method must be 'std' or 'percentile'")

        pred_segments = [0]
        current_segment = 0
        last_boundary = 0

        for i in range(1, num_sentences):
            if sims[i - 1] < threshold and (i - last_boundary) >= min_size:
                current_segment += 1
                last_boundary = i
            pred_segments.append(current_segment)

        return pred_segments, threshold

    #TODO: Improve topic extraction
    @staticmethod
    def _get_segment_topics(sentences, segments, top_n=1):
        segment_dict = {}
        for seg_id in sorted(set(segments)):
            seg_sentences = [s for s, sid in zip(sentences, segments) if sid == seg_id]
            seg_text = " ".join(seg_sentences)

            vectorizer = TfidfVectorizer(stop_words="english")
            X = vectorizer.fit_transform([seg_text])

            words = np.array(vectorizer.get_feature_names_out())
            scores = X.toarray()[0]

            top_indices = scores.argsort()[::-1][:top_n]
            segment_dict[seg_id] = words[top_indices].tolist()

        return segment_dict