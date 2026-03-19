import pytest
import os
import json
from unittest.mock import MagicMock
from app.services.storage import StorageManager
from app.services.recordings import RecordingService
from app.core.config import settings

@pytest.fixture
def storage_manager():
    return StorageManager()

@pytest.fixture
def recording_service(storage_manager):
    return RecordingService(storage_manager)

def test_storage_save_load_json(storage_manager):
    data = {"hello": "world"}
    rel_path = "test/data.json"
    saved_path = storage_manager.save_json(rel_path, data)
    assert saved_path == rel_path
    
    loaded = storage_manager.load_json(rel_path)
    assert loaded == data

def test_storage_metadata(storage_manager):
    rec_id = "test_rec"
    meta = {"title": "Test Recording", "audio": "audio/path.wav"}
    storage_manager.save_metadata(rec_id, meta)
    
    loaded = storage_manager.load_metadata(rec_id)
    assert loaded["title"] == "Test Recording"

def test_recordings_list_empty(recording_service):
    recordings = recording_service.list_recordings()
    assert recordings == []

def test_recordings_list_with_data(recording_service, storage_manager):
    rec_id = "rec123"
    meta = {
        "title": "My Title",
        "created_at": "2024-01-24T12:00:00",
        "audio": "audio/rec123.wav",
        "transcripts": {"original": "transcripts/rec123/original.txt"}
    }
    storage_manager.save_metadata(rec_id, meta)
    
    # Save dummy transcript file
    os.makedirs(os.path.join(settings.DATA_DIR, "transcripts/rec123"), exist_ok=True)
    with open(os.path.join(settings.DATA_DIR, "transcripts/rec123/original.txt"), "w") as f:
        f.write("Hello world transcript")
        
    recordings = recording_service.list_recordings()
    assert len(recordings) == 1
    assert recordings[0]["recording_id"] == rec_id
    assert recordings[0]["title"] == "My Title"
    assert recordings[0]["search_text"] == "Hello world transcript"

def test_get_recording_full(recording_service, storage_manager):
    rec_id = "rec_full"
    meta = {
        "title": "Full Rec",
        "transcripts": {"original": "transcripts/rec_full/original.txt"}
    }
    storage_manager.save_metadata(rec_id, meta)
    
    os.makedirs(os.path.join(settings.DATA_DIR, "transcripts/rec_full"), exist_ok=True)
    with open(os.path.join(settings.DATA_DIR, "transcripts/rec_full/original.txt"), "w") as f:
        f.write("Full transcript text")
        
    full = recording_service.get_recording_full(rec_id)
    assert full is not None
    assert full["title"] == "Full Rec"
    assert full["transcript"] == "Full transcript text"
