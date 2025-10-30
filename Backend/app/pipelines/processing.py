# app/pipelines/processing.py
from app.domain.models import Recording
from app.services.transcription import TranscriptionManager
from app.services.segmentation import SegmentationManager
from app.services.pii import PIIDetector
from app.services.storage import StorageManager

store = StorageManager()
transcriber = TranscriptionManager()
segmenter = SegmentationManager()
pii = PIIDetector()

def process_uploaded_audio(filename: str, file_bytes: bytes, language="en"):
    rec_id, path = store.save_upload(filename, file_bytes)
    rec = Recording(id=rec_id, path=path, language=language)

    transcript = transcriber.transcribe(rec)
    segments = segmenter.segment(transcript)
    pii_hits = pii.detect(transcript)

    return {
        "recording_id": rec.id,
        "transcript": transcript.text,
        "segments": [s.__dict__ for s in segments],
        "pii": [p.__dict__ for p in pii_hits],
    }
