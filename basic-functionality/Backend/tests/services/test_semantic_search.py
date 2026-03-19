import pytest
import numpy as np
import os
from unittest.mock import MagicMock, patch
from app.services.semantic_search import SemanticSearchManager
from app.core.config import settings

@pytest.fixture
def mock_search_deps():
    with patch("app.services.semantic_search.SentenceTransformer") as mock_st, \
         patch("app.services.semantic_search.StorageManager") as mock_storage, \
         patch("app.services.semantic_search.cosine_similarity") as mock_cos:
        
        # Mock SentenceTransformer
        mock_model = MagicMock()
        mock_st.return_value = mock_model
        
        # Mock StorageManager
        mock_store = MagicMock()
        mock_storage.return_value = mock_store
        
        yield mock_model, mock_store, mock_cos

@pytest.fixture
def search_manager(mock_search_deps):
    return SemanticSearchManager()

def test_search_empty_query(search_manager):
    assert search_manager.search("") == []

def test_search_no_recordings(search_manager):
    # Ensure metadata directory is empty or non-existent in this test
    # (The test_setup fixture clears the DATA_DIR)
    assert search_manager.search("test") == []

def test_search_basic(search_manager, mock_search_deps):
    mock_model, mock_store, mock_cos = mock_search_deps
    
    # Mock some data exists
    # We need to mock os.listdir and os.path.isdir as well because they are used in search()
    with patch("os.listdir") as mock_listdir, \
         patch("os.path.isdir") as mock_isdir:
        
        mock_isdir.return_value = True
        mock_listdir.return_value = ["rec1.json", "rec2.json"]
        
        # Mock metadata loading
        mock_store.load_metadata.side_effect = [
            {"segments": ["segments/rec1.json"]},
            {"segments": ["segments/rec2.json"]}
        ]
        
        # Mock segments loading
        mock_store.load_json.side_effect = [
            {"segments": [{"id": 0, "text": "Pizza is great", "label": "food"}]},
            {"segments": [{"id": 1, "text": "The weather is sunny", "label": "weather"}]}
        ]
        
        # Mock embedding return values
        mock_model.encode.side_effect = [
            np.random.rand(1, 384), # query
            np.random.rand(2, 384)  # 2 candidates
        ]
        
        # Mock cosine similarity: [rec1_seg0, rec2_seg1]
        mock_cos.return_value = np.array([[0.8, 0.1]])
        
        hits = search_manager.search("Tell me about food")
        
        assert len(hits) == 1
        assert hits[0].recording_id == "rec1"
        assert hits[0].text == "Pizza is great"
        assert hits[0].score == 0.8

def test_search_capping(search_manager, mock_search_deps):
    mock_model, mock_store, mock_cos = mock_search_deps
    
    with patch("os.listdir") as mock_listdir, patch("os.path.isdir") as mock_isdir:
        mock_isdir.return_value = True
        mock_listdir.return_value = ["rec1.json"]
        
        mock_store.load_metadata.return_value = {"segments": ["segments/rec1.json"]}
        # 3 segments in one recording
        mock_store.load_json.return_value = {"segments": [
            {"id": 0, "text": "First", "label": "L"},
            {"id": 1, "text": "Second", "label": "L"},
            {"id": 2, "text": "Third", "label": "L"}
        ]}
        
        mock_model.encode.side_effect = [
            np.random.rand(1, 384),
            np.random.rand(3, 384)
        ]
        
        # All have high score
        mock_cos.return_value = np.array([[0.9, 0.8, 0.7]])
        
        # Search with per_recording_cap=2
        hits = search_manager.search("query", per_recording_cap=2)
        
        assert len(hits) == 2
        assert hits[0].recording_id == "rec1"
        assert hits[1].recording_id == "rec1"
