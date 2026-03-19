import pytest
import numpy as np
from app.services.prosody import ProsodyManager
from app.domain.models import Transcript, Sentence

@pytest.fixture
def prosody_manager():
    return ProsodyManager()

def test_analyze_sentences_empty(prosody_manager):
    transcript = Transcript(recording_id="rec1", text="", sentences=[])
    audio = np.zeros(16000)
    features = prosody_manager.analyze_sentences(transcript, audio)
    assert features == []

def test_analyze_sentence_basic(prosody_manager):
    # 1 second of audio at 16k SR
    sample_rate = 16000
    audio = np.random.uniform(-0.1, 0.1, sample_rate)
    
    sentence = Sentence(
        id=1,
        start_s=0.0,
        end_s=1.0,
        text="This is a test sentence.",
        meta={"recording_id": "rec1"}
    )
    
    pf = prosody_manager._analyze_sentence(sentence, audio)
    
    assert pf is not None
    assert pf.sentence_id == 1
    assert pf.rms_mean > 0
    assert pf.rms_var >= 0
    # 6 words in 1 second = 6 words * 60 seconds = 360 WPM
    assert pf.speaking_rate_wpm == 300.0 # 5 words: This(1) is(2) a(3) test(4) sentence.(5)
    assert pf.pause_ratio >= 0 and pf.pause_ratio <= 1.0

def test_analyze_sentence_out_of_bounds(prosody_manager):
    audio = np.zeros(1000)
    sentence = Sentence(id=1, start_s=0.0, end_s=2.0, text="Too long")
    pf = prosody_manager._analyze_sentence(sentence, audio)
    assert pf is None

def test_analyze_sentence_invalid_range(prosody_manager):
    audio = np.zeros(16000)
    sentence = Sentence(id=1, start_s=1.0, end_s=0.5, text="Invalid")
    pf = prosody_manager._analyze_sentence(sentence, audio)
    assert pf is None
