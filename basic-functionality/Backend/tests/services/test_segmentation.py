import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from app.services.segmentation import SegmentationManager
from app.domain.models import Transcript, Sentence

@pytest.fixture
def mock_models():
    with patch("app.services.segmentation.SentenceTransformer") as mock_st, \
         patch("app.services.segmentation.spacy.load") as mock_spacy:
        
        # Mock SentenceTransformer
        mock_model = MagicMock()
        mock_st.return_value = mock_model
        # Return dummy embeddings
        mock_model.encode.side_effect = lambda texts, **kwargs: np.random.rand(len(texts), 384).astype(np.float32)
        
        # Mock spaCy
        mock_nlp = MagicMock()
        mock_spacy.return_value = mock_nlp
        # Mock noun chunks for labeling
        mock_chunk = MagicMock()
        mock_chunk.text = "test topic"
        mock_doc = MagicMock()
        mock_doc.noun_chunks = [mock_chunk]
        mock_nlp.return_value = mock_doc
        
        yield mock_model, mock_nlp

@pytest.fixture
def segmentation_manager(mock_models):
    with patch("app.services.segmentation.settings") as mock_settings:
        mock_settings.SEGMENTATION_MODEL = "mock-model"
        mock_settings.SEGMENTATION_STRATEGY = "adaptive"
        mock_settings.SEGMENTATION_SIMILARITY_METHOD = "percentile"
        mock_settings.SEGMENTATION_STD_FACTOR = 1.0
        mock_settings.SEGMENTATION_MIN_SIZE = 1
        mock_settings.SEGMENTATION_PERCENTILE = 20
        mock_settings.SEGMENTATION_TOPIC_TOP_N = 1
        return SegmentationManager()

def test_segment_short(segmentation_manager):
    transcript = Transcript(recording_id="rec1", text="Short", sentences=[Sentence(id=1, start_s=0, end_s=1, text="Short")])
    segments = segmentation_manager.segment(transcript, "rec1")
    assert len(segments) == 1
    assert segments[0].label == "short transcript"

def test_segment_basic(segmentation_manager):
    sentences = [
        Sentence(id=1, start_s=0, end_s=5, text="This is the first sentence about food."),
        Sentence(id=2, start_s=5, end_s=10, text="I really like eating pizza and pasta."),
        Sentence(id=3, start_s=10, end_s=15, text="Now let's talk about something else entirely."),
        Sentence(id=4, start_s=15, end_s=20, text="The weather today is quite sunny and warm.")
    ]
    transcript = Transcript(recording_id="rec1", text=" ".join(s.text for s in sentences), sentences=sentences)
    
    # Mock cosine_similarity in the manager.
    # Re-import it to be sure we patch the right one
    with patch("app.services.segmentation.cosine_similarity") as mock_cos:
        # Return high similarity for s1-s2, low for s2-s3, high for s3-s4
        # and then enough values for the labeling phase
        mock_cos.side_effect = [
            np.array([[0.9]]), # s1-s2
            np.array([[0.1]]), # s2-s3
            np.array([[0.9]]), # s3-s4
            np.array([[0.9, 0.8]]), # labeling segment 0
            np.array([[0.9, 0.8]]), # labeling segment 1
        ]
        
        segments = segmentation_manager.segment(transcript, "rec1")
        
        # With percentile=20, 0.1 should definitely be below threshold (0.1, 0.9, 0.9)
        assert len(segments) >= 1
        # Check that we have at least one split
        seg_ids = [s.id for s in segments]
        assert len(set(seg_ids)) >= 2

def test_phrase_ok(segmentation_manager):
    assert segmentation_manager._phrase_ok("Natural Language Processing") == True
    assert segmentation_manager._phrase_ok("i") == False
    assert segmentation_manager._phrase_ok("!!!") == False
    assert segmentation_manager._phrase_ok("this thing") == False # stoplike

def test_clean_phrase(segmentation_manager):
    assert segmentation_manager._clean_phrase("  Hello   World  ") == "Hello World"
