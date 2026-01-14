# app/pipelines/processing.py
from ..domain.models import Recording
from ..services.transcription import TranscriptionManager
from ..services.segmentation import SegmentationManager
from ..services.pii import PIIDetector
from ..services.storage import StorageManager

store = StorageManager()
transcriber = TranscriptionManager()
segmenter = SegmentationManager()
pii = PIIDetector()

def process_uploaded_audio(filename: str, file_bytes: bytes, language="en"):
    rec_id, path = store.save_upload(filename, file_bytes)
    rec = Recording(id=rec_id, path=path, language=language)

    transcript = transcriber.transcribe(rec)
    pii_hits = pii.detect(transcript)
    original_path = store.save_transcript(rec_id, transcript.text, version="original")
    
    # optioneel: redacted versie opslaan
    redacted_text = pii.redact(transcript.text)
    redacted_path = store.save_transcript(rec_id, redacted_text, version="redacted")

    metadata = {
        "recording_id": rec_id,
        "audio": path,
        "transcripts": {
            "original": original_path,
            "edited": None,
            "redacted": redacted_path
        },
        "segments": [],
        "pii": [p.__dict__ for p in pii_hits],
        "created_at": rec.created_at if hasattr(rec, "created_at") else None
    }
    store.save_metadata(rec_id, metadata)

    return {
        "recording_id": rec.id,
        "transcript": transcript,
        "pii": [p.__dict__ for p in pii_hits],
    }

def process_after_edit(recording_id: str, edited_text: str):
    edited_path = store.save_transcript(recording_id, edited_text, version="edited")

    segments = segmenter.segment(edited_text, recording_id)
    segments_path = store.save_segments(recording_id, segments)

    meta = store.load_metadata(recording_id)
    meta.setdefault("transcripts", {})
    meta.setdefault("segments", [])

    meta["transcripts"]["edited"] = edited_path
    meta["segments"] = [segments_path]

    store.save_metadata(recording_id, meta)

    return {
        "recording_id": recording_id,
        "segments": [s.__dict__ for s in segments],
        "status": "saved"
    }


