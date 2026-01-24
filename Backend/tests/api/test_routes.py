import pytest
from unittest.mock import MagicMock
from app.api.deps import (
    get_storage_manager, get_recording_service, get_settings_manager,
    get_transcription_manager, get_pii_detector, get_prosody_manager,
    get_segmentation_manager
)
from app.main import app

@pytest.fixture
def mock_storage():
    return MagicMock()

@pytest.fixture
def mock_recording_service():
    return MagicMock()

@pytest.fixture
def mock_settings_manager():
    return MagicMock()

@pytest.fixture
def mock_transcription_manager():
    return MagicMock()

@pytest.fixture
def mock_pii_detector():
    return MagicMock()

@pytest.fixture
def mock_segmenter():
    return MagicMock()

@pytest.fixture(autouse=True)
def setup_overrides(
    mock_storage, mock_recording_service, mock_settings_manager,
    mock_transcription_manager, mock_pii_detector, mock_segmenter
):
    # Use FastAPI dependency_overrides for CLEAN testing
    app.dependency_overrides[get_storage_manager] = lambda: mock_storage
    app.dependency_overrides[get_recording_service] = lambda: mock_recording_service
    app.dependency_overrides[get_settings_manager] = lambda: mock_settings_manager
    app.dependency_overrides[get_transcription_manager] = lambda: mock_transcription_manager
    app.dependency_overrides[get_pii_detector] = lambda: mock_pii_detector
    app.dependency_overrides[get_segmentation_manager] = lambda: mock_segmenter
    
    yield
    
    app.dependency_overrides = {}

def test_get_settings(client, mock_settings_manager):
    mock_settings_manager.get_effective_settings.return_value = {"TEST": True}
    response = client.get("/api/settings")
    assert response.status_code == 200
    assert response.json()["settings"]["TEST"] is True

def test_list_recordings(client, mock_recording_service):
    mock_recording_service.list_recordings.return_value = [{"recording_id": "rec1"}]
    response = client.get("/api/recordings")
    assert response.status_code == 200
    assert len(response.json()) == 1

def test_get_recording_404(client, mock_recording_service):
    mock_recording_service.get_recording_full.return_value = None
    response = client.get("/api/recordings/missing")
    assert response.status_code == 404

def test_upload_recording(client, mock_storage, mock_transcription_manager, mock_pii_detector):
    # Mock pipeline inputs/outputs indirectly via injected mocks
    mock_storage.save_upload.return_value = ("rec_new", "audio/path.wav")
    mock_storage.abs_path.return_value = "/abs/path.wav"
    
    mock_transcription = MagicMock()
    mock_transcription.text = "hi"
    mock_transcription.sentences = []
    mock_transcription.words = []
    mock_transcription_manager.transcribe.return_value = mock_transcription
    
    mock_pii_detector.detect.return_value = []
    
    files = {"file": ("test.wav", b"fake wav data", "audio/wav")}
    response = client.post("/api/recordings/upload", files=files, data={"language": "en"})
    
    assert response.status_code == 200
    assert response.json()["recording_id"] == "rec_new"

def test_finalize_recording(client, mock_storage, mock_segmenter, mock_pii_detector):
    mock_storage.load_metadata.return_value = {"sentences": []}
    mock_storage.save_transcript.return_value = "path/to/edited.txt"
    mock_storage.save_segments.return_value = "path/to/segments.json"
    mock_storage.exists_rel.return_value = False
    
    mock_segmenter.segment.return_value = []
    mock_pii_detector.detect.return_value = []
    
    response = client.post("/api/recordings/finalize", data={
        "recording_id": "rec1",
        "edited_transcript": "Corrected text"
    })
    
    assert response.status_code == 200
    assert response.json()["status"] == "saved"
