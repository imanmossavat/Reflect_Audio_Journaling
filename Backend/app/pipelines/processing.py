# app/pipelines/processing.py
from datetime import datetime, timezone

from app.domain.models import Recording
from app.services.transcription import TranscriptionManager
from app.services.segmentation import SegmentationManager
from app.services.pii import PIIDetector
from app.services.storage import StorageManager

store = StorageManager()
transcriber = TranscriptionManager()
segmenter = SegmentationManager()
pii = PIIDetector()


def fallback_title(created_at_iso: str) -> str:
    try:
        dt = datetime.fromisoformat(created_at_iso.replace("Z", "+00:00"))
        return dt.strftime("Recording · %Y-%m-%d %H:%M")
    except Exception:
        return "Recording"


def process_uploaded_audio(filename: str, file_bytes: bytes, language: str = "en"):
    """
    Upload pipeline:
    - Save upload (store rel path)
    - Convert rel -> abs for processing
    - Transcribe
    - Detect PII
    - Save original transcript
    - Save redacted transcript with labels (REDACTED:<LABEL>)
    - Save metadata
    """
    rec_id, audio_rel = store.save_upload(filename, file_bytes)
    audio_abs = store.abs_path(audio_rel)

    rec = Recording(id=rec_id, path=audio_abs, language=language)

    # created_at must always exist in metadata
    created_at = (
        rec.created_at
        if hasattr(rec, "created_at") and rec.created_at is not None
        else datetime.now(timezone.utc).isoformat()
    )

    # --- Transcription ---
    transcript = transcriber.transcribe(rec)
    if transcript is None or not getattr(transcript, "text", None):
        # make failures loud and explicit
        raise RuntimeError("Transcription failed: no transcript text returned")

    # --- PII detection (once) ---
    pii_hits = pii.detect(transcript)  # detections on original
    redacted_text = pii.redact(transcript.text, pii_hits)  # redacted from original
    redacted_path = store.save_transcript(rec_id, redacted_text, version="redacted")
    
    # --- Save transcripts ---
    original_path = store.save_transcript(rec_id, transcript.text, version="original")

    # typed redaction should be done using the SAME text the offsets refer to
    # use your new method name; change if you named it differently
    if hasattr(pii, "redact_with_labels"):
        redacted_text = pii.redact_with_labels(transcript.text, pii_hits)
    else:
        # fallback (still typed) if you kept the old name "redact"
        # expected signature: redact(text, hits)
        redacted_text = pii.redact(transcript.text, pii_hits)

    redacted_path = store.save_transcript(rec_id, redacted_text, version="redacted")

    # --- Metadata ---
    metadata = {
        "recording_id": rec_id,
        "audio": audio_rel,
        "transcripts": {
            "original": original_path,
            "edited": None,
            "redacted": redacted_path,
        },
        "segments": [],
        "pii_original": [p.__dict__ for p in pii_hits],
        "pii_edited": [],
        "pii": [p.__dict__ for p in pii_hits],
        "created_at": created_at,
        "title": fallback_title(created_at),
        "tags": [],
    }
    store.save_metadata(rec_id, metadata)

    return {
        "recording_id": rec.id,
        "transcript": transcript,
        "pii": [p.__dict__ for p in pii_hits],
    }
    
def process_after_edit(recording_id: str, edited_text: str):
    """
    After user edits:
    - Save edited transcript
    - Segment edited text
    - Save segments file
    - Update metadata
    - Optionally set title from first segment label if title is still default-ish
    """
    edited_path = store.save_transcript(recording_id, edited_text, version="edited")

    segments = segmenter.segment(edited_text, recording_id)
    segments_path = store.save_segments(recording_id, segments)

    # 🔥 rerun PII on edited
    edited_transcript = type("Transcript", (), {"recording_id": recording_id, "text": edited_text})
    pii_hits_edited = pii.detect(edited_transcript)

    # 🔥 redacted must be based on edited
    redacted_text = pii.redact(edited_text, pii_hits_edited)
    redacted_path = store.save_transcript(recording_id, redacted_text, version="redacted")

    meta = store.load_metadata(recording_id)
    meta.setdefault("transcripts", {})
    meta.setdefault("segments", [])

    meta["transcripts"]["edited"] = edited_path
    meta["transcripts"]["redacted"] = redacted_path
    meta["segments"] = [segments_path]

    meta.setdefault("pii_original", meta.get("pii", []))
    meta["pii_edited"] = [p.__dict__ for p in pii_hits_edited]

    # optional compat
    meta["pii"] = meta["pii_edited"]

    store.save_metadata(recording_id, meta)

    return {
        "recording_id": recording_id,
        "segments": [s.__dict__ for s in segments],
        "pii_edited": [p.__dict__ for p in pii_hits_edited],
        "status": "saved",
    }