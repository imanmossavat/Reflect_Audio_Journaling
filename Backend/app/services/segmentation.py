import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import SpectralCoclustering
from sentence_transformers import SentenceTransformer
from app.domain.models import Segment
from app.core.config import settings

class SegmentationManager:
    """
    Handles topic segmentation on transcript text using sentence embeddings and clustering.
    """

    def __init__(self):
        self.model = SentenceTransformer(settings.SEGMENTATION_MODEL)
        self.method = settings.SEGMENTATION_METHOD
        self.std_factor = settings.SEGMENTATION_STD_FACTOR
        self.min_size = settings.SEGMENTATION_MIN_SIZE
        self.percentile = settings.SEGMENTATION_PERCENTILE
        self.top_n = settings.SEGMENTATION_TOPIC_TOP_N

    def segment(self, transcript, method="adaptive"):
        """
        Segment transcript text into coherent topic sections.
        Returns a list of Segment objects.
        """

        sentences = self._split_sentences(transcript.text)
        if len(sentences) < 3:
            return [Segment(recording_id=transcript.recording_id, start_s=0, end_s=0, label="short transcript")]

        # Encode to embeddings
        embeddings = self.model.encode(sentences)

        if method == "spectral":
            seg_ids, boundaries, labels = self._spectral_segmentation(sentences)
        else:
            seg_ids, threshold = self._adaptive_threshold_segmentation(embeddings)

        topics = self._get_segment_topics(sentences, seg_ids)

        segments = []
        for seg_id, topic in topics.items():
            segments.append(
                Segment(
                    recording_id=transcript.recording_id,
                    start_s=0,
                    end_s=0,
                    label=topic[0] if topic else f"Segment {seg_id}",
                    text=" ".join([s for s, sid in zip(sentences, seg_ids) if sid == seg_id])
                )
            )
        return segments

    # ---------------- Helper Methods ---------------- #

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
        """
        Convert a list of boundary indices into segment IDs.
        Ensures that each sentence gets a segment number.
        """
        segments = [0] * num_sentences
        current = 0
        last_boundary = -1
        filtered_boundaries = []

        for b in boundaries:
            if b - last_boundary >= min_size:
                filtered_boundaries.append(b)
                last_boundary = b

        for i in range(num_sentences):
            segments[i] = current
            if i in filtered_boundaries:
                current += 1

        return segments

    @staticmethod
    def _split_sentences(text: str):
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        return [s for s in sentences if s]

    @staticmethod
    def _adaptive_threshold_segmentation(embeddings, method="std", min_size=2, std_factor=1.0, percentile=20):
        num_sentences = embeddings.shape[0]
        sims = [cosine_similarity(embeddings[i-1].reshape(1,-1), embeddings[i].reshape(1,-1))[0][0] for i in range(1, num_sentences)]
        sims = np.array(sims)

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
            sim = cosine_similarity(embeddings[i-1].reshape(1,-1), embeddings[i].reshape(1,-1))[0][0]
            if sim < threshold and (i - last_boundary) >= min_size:
                current_segment += 1
                last_boundary = i
            pred_segments.append(current_segment)

        return pred_segments, threshold

    @staticmethod
    def _get_segment_topics(sentences, segments, top_n=1):
        segment_dict = {}
        unique_segments = sorted(set(segments))
        for seg_id in unique_segments:
            seg_sentences = [s for s, seg in zip(sentences, segments) if seg == seg_id]
            seg_text = " ".join(seg_sentences)

            vectorizer = TfidfVectorizer(stop_words='english')
            X = vectorizer.fit_transform([seg_text])
            feature_array = np.array(vectorizer.get_feature_names_out())
            tfidf_scores = X.toarray()[0]

            top_indices = tfidf_scores.argsort()[::-1][:top_n]
            top_words = feature_array[top_indices].tolist()
            segment_dict[seg_id] = top_words

        return segment_dict