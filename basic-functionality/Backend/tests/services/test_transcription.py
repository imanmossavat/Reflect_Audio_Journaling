import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from app.services.transcription import TranscriptionManager
from app.domain.models import Recording

@pytest.fixture
def mock_whisperx():
    with patch("app.services.transcription.whisperx.load_model") as mock_load_model, \
         patch("app.services.transcription.whisperx.load_align_model") as mock_load_align, \
         patch("app.services.transcription.whisperx.align") as mock_align:
        
        mock_asr = MagicMock()
        mock_load_model.return_value = mock_asr
        
        mock_align_model = MagicMock()
        mock_align_metadata = {"language": "en"}
        mock_load_align.return_value = (mock_align_model, mock_align_metadata)
        
        yield mock_asr, mock_align_model, mock_align

@pytest.fixture
def transcription_manager(mock_whisperx):
    with patch("app.services.transcription.settings") as mock_settings:
        mock_settings.DEVICE = "cpu"
        mock_settings.WHISPER_MODEL = "tiny"
        mock_settings.COMPUTE_TYPE = "float32"
        mock_settings.LANGUAGE = "en"
        return TranscriptionManager()

def test_transcribe_basic(transcription_manager, mock_whisperx):
    mock_asr, mock_align_model, mock_align = mock_whisperx
    
    recording = Recording(id="rec1", path="fake.wav")
    
    # Mock audio loading
    with patch.object(TranscriptionManager, "_load_audio_ffmpeg") as mock_load_audio:
        mock_load_audio.return_value = np.zeros(16000)
        
        # Mock ASR result
        mock_asr.transcribe.return_value = {"segments": [{"text": "hello"}], "language": "en"}
        
        # Mock alignment result
        mock_align.return_value = {
            "segments": [
                {
                    "text": "hello",
                    "start": 0.0,
                    "end": 1.0,
                    "words": [{"word": "hello", "start": 0.0, "end": 1.0, "score": 0.9}]
                }
            ]
        }
        
        transcript = transcription_manager.transcribe(recording)
        
        assert transcript.text == "hello"
        assert len(transcript.words) == 1
        assert transcript.words[0].word == "hello"
        assert len(transcript.sentences) == 1
        assert transcript.sentences[0].text == "hello"

def test_load_audio_ffmpeg_mock(transcription_manager):
    with patch("subprocess.run") as mock_run, patch("os.path.exists") as mock_exists:
        mock_exists.return_value = True
        
        # Mock ffmpeg output: 1 second of 16kHz 16-bit mono = 32000 bytes
        dummy_audio = np.zeros(16000, dtype=np.int16).tobytes()
        mock_run.return_value = MagicMock(returncode=0, stdout=dummy_audio)
        
        audio = transcription_manager._load_audio_ffmpeg("fake.wav")
        assert audio.dtype == np.float32
        assert audio.size == 16000
