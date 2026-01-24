import pytest
from unittest.mock import MagicMock, patch
from app.services.pii import PIIDetector
from app.domain.models import Transcript, PiiFinding

@pytest.fixture
def mock_spacy_nlp():
    with patch("spacy.load") as mock_load:
        mock_nlp = MagicMock()
        mock_load.return_value = mock_nlp
        # Mock entity detection
        mock_ent = MagicMock()
        mock_ent.label_ = "PERSON"
        mock_ent.text = "John Doe"
        mock_ent.start_char = 0
        mock_ent.end_char = 8
        mock_nlp.return_value.ents = [mock_ent]
        yield mock_nlp

@pytest.fixture
def pii_detector(mock_spacy_nlp):
    with patch("app.services.pii.settings") as mock_settings:
        mock_settings.LANGUAGE = "en"
        mock_settings.PII_PATTERNS = {
            "EMAIL": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
            "PHONE": r"\d{3}-\d{3}-\d{4}"
        }
        return PIIDetector()

def test_detect_regex(pii_detector):
    transcript = Transcript(
        recording_id="test_rec",
        text="My email is test@example.com and phone is 123-456-7890."
    )
    # Clear spaCy entities for this test to focus on regex
    pii_detector.nlp.return_value.ents = []
    
    findings = pii_detector.detect(transcript)
    
    labels = [f.label for f in findings]
    assert "EMAIL" in labels
    assert "PHONE" in labels
    assert any(f.preview == "test@example.com" for f in findings)
    assert any(f.preview == "123-456-7890" for f in findings)

def test_detect_spacy(pii_detector):
    transcript = Transcript(
        recording_id="test_rec",
        text="John Doe lives in Amsterdam."
    )
    # Mock spaCy output
    mock_ent1 = MagicMock(label_="PERSON", text="John Doe", start_char=0, end_char=8)
    mock_ent2 = MagicMock(label_="GPE", text="Amsterdam", start_char=18, end_char=27)
    pii_detector.nlp.return_value.ents = [mock_ent1, mock_ent2]
    
    # Ensure patterns don't match nothing
    pii_detector.patterns = {}
    
    findings = pii_detector.detect(transcript)
    
    labels = [f.label for f in findings]
    assert "PERSON" in labels
    assert "GPE" in labels
    assert any(f.preview == "John Doe" for f in findings)
    assert any(f.preview == "Amsterdam" for f in findings)

def test_redact(pii_detector):
    text = "Hello John Doe, your email is test@example.com."
    findings = [
        PiiFinding(recording_id="rec1", start_char=6, end_char=14, label="PERSON", preview="John Doe"),
        PiiFinding(recording_id="rec1", start_char=30, end_char=46, label="EMAIL", preview="test@example.com")
    ]
    
    redacted = pii_detector.redact(text, findings)
    assert "[REDACTED:PERSON]" in redacted
    assert "[REDACTED:EMAIL]" in redacted
    assert "John Doe" not in redacted
    assert "test@example.com" not in redacted

def test_redact_overlaps(pii_detector):
    text = "My name is John Doe."
    # Overlapping findings: "John Doe" (0-8) and "John" (0-4) - relative to "John Doe"
    # Actually 11-19 is "John Doe"
    findings = [
        PiiFinding(recording_id="rec1", start_char=11, end_char=19, label="PERSON", preview="John Doe"),
        PiiFinding(recording_id="rec1", start_char=11, end_char=15, label="FIRSTNAME", preview="John")
    ]
    
    redacted = pii_detector.redact(text, findings)
    # Overlap should be merged
    assert "[REDACTED:PERSON+FIRSTNAME]" in redacted or "[REDACTED:FIRSTNAME+PERSON]" in redacted
    assert "John Doe" not in redacted
