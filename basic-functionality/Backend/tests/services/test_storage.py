import os
import pytest

from app.services.storage import StorageManager

@pytest.fixture
def storage():
    return StorageManager()

def test_storage_init(storage):
    assert os.path.isdir(storage.base)

def test_save_upload(storage):
    content = b"fake audio data"
    rec_id, rel_path = storage.save_upload("test audio.wav", content)
    
    assert rec_id is not None
    assert os.path.exists(storage.abs_path(rel_path))
    with open(storage.abs_path(rel_path), "rb") as f:
        assert f.read() == content

def test_save_load_transcript(storage):
    rec_id = "test_rec"
    text = "Hello transcript"
    rel_path = storage.save_transcript(rec_id, text, version="edited")
    
    assert "edited.txt" in rel_path
    assert storage.load_text(rel_path) == text

def test_save_load_json(storage):
    data = {"key": "value"}
    rel_path = "test.json"
    storage.save_json(rel_path, data)
    assert storage.load_json(rel_path) == data

def test_metadata_lifecycle(storage):
    rec_id = "rec123"
    meta = {"title": "Test Title", "audio": "audio/123.wav"}
    storage.save_metadata(rec_id, meta)
    
    loaded = storage.load_metadata(rec_id)
    assert loaded["title"] == "Test Title"
    
    os.makedirs(storage.abs_path("audio"), exist_ok=True)
    with open(storage.abs_path("audio/123.wav"), "w") as f: f.write("dummy")
    
    success = storage.delete_audio(rec_id)
    assert success is True
    assert storage.load_metadata(rec_id)["audio"] is None

def test_delete_recording(storage):
    rec_id = "to_delete"
    storage.save_metadata(rec_id, {"title": "Gone Soon"})
    storage.save_transcript(rec_id, "Some text")
    
    storage.delete_recording(rec_id)
    assert not os.path.exists(storage.abs_path(f"metadata/{rec_id}.json"))
    assert not os.path.exists(storage.abs_path(f"transcripts/{rec_id}"))

def test_prune_empty_parents(storage):
    deep_path = storage.abs_path("a/b/c/d")
    os.makedirs(deep_path, exist_ok=True)
    
    storage.engine.prune_empty_dirs(deep_path)
    
    assert not os.path.exists(storage.abs_path("a"))
    assert os.path.exists(storage.base)
