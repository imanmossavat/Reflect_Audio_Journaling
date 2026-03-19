import pytest
from unittest.mock import MagicMock
from app.pipelines.processing import process_uploaded_audio, process_after_edit, process_text_entry
from app.domain.models import Transcript, Sentence, PiiFinding

@pytest.fixture
def mock_storage():
    return MagicMock()

@pytest.fixture
def mock_transcriber():
    return MagicMock()

@pytest.fixture
def mock_segmenter():
    return MagicMock()

@pytest.fixture
def mock_prosody():
    return MagicMock()

@pytest.fixture
def mock_pii():
    return MagicMock()

def test_process_uploaded_audio(mock_storage, mock_transcriber, mock_pii):
    # Mock storage behavior
    mock_storage.save_upload.return_value = ("rec1", "audio/rec1.wav")
    mock_storage.abs_path.return_value = "/abs/audio/rec1.wav"
    mock_storage.save_words.return_value = "words.json"
    mock_storage.save_transcript.side_effect = ["orig.txt", "redact.txt"]
    
    # Mock transcriber
    mock_transcript = Transcript(
        recording_id="rec1",
        text="Hello world",
        sentences=[Sentence(id=0, start_s=0, end_s=1, text="Hello world")],
        words=[]
    )
    mock_transcriber.transcribe.return_value = mock_transcript
    
    # Mock PII
    mock_pii.detect.return_value = []
    mock_pii.redact.return_value = "Hello world"
    
    result = process_uploaded_audio(
        "test.wav", b"fake data", 
        storage=mock_storage, 
        transcriber=mock_transcriber, 
        pii_service=mock_pii
    )
    
    assert result["recording_id"] == "rec1"
    assert result["transcript"]["text"] == "Hello world"
    mock_storage.save_metadata.assert_called_once()

def test_process_after_edit(mock_storage, mock_transcriber, mock_segmenter, mock_pii, mock_prosody):
    rec_id = "rec1"
    mock_storage.load_metadata.return_value = {
        "sentences": [{"id": 0, "start_s": 0.0, "end_s": 1.0, "text": "Old text"}],
        "audio": "audio/rec1.wav"
    }
    mock_storage.save_transcript.return_value = "edited.txt"
    mock_storage.save_segments.return_value = "segments.json"
    mock_storage.abs_path.return_value = "/abs/path.wav"
    
    mock_segmenter.segment.return_value = []
    mock_pii.detect.return_value = []
    mock_pii.redact.return_value = "Edited text"
    
    result = process_after_edit(
        rec_id, "Edited text",
        storage=mock_storage,
        segmenter=mock_segmenter,
        pii_service=mock_pii,
        prosody_service=mock_prosody,
        transcriber=mock_transcriber
    )
    
    assert result["recording_id"] == rec_id
    assert result["status"] == "saved"
    mock_storage.save_metadata.assert_called_once()

def test_process_text_entry(mock_storage, mock_segmenter, mock_pii):
    mock_storage.save_transcript.return_value = "orig.txt"
    mock_segmenter.segment.return_value = []
    mock_pii.detect.return_value = []
    
    result = process_text_entry(
        "Just some text", 
        storage=mock_storage, 
        segmenter=mock_segmenter, 
        pii_service=mock_pii,
        title="My Title"
    )
    
    assert result["status"] == "ok"
    assert "recording_id" in result
    mock_storage.save_metadata.assert_called_once()
