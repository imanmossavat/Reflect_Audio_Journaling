# app/pipelines/processing.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.domain.models import Recording
from app.services.transcription import TranscriptionManager
from app.services.segmentation import SegmentationManager
from app.services.pii import PIIDetector
from app.services.storage import StorageManager

store = StorageManager()
transcriber = TranscriptionManager()
segmenter = SegmentationManager()
pii = PIIDetector()


# =============================================================================
# Helpers
# =============================================================================

def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fallback_title(created_at_iso: str) -> str:
    """
    Used when we don't have anything better. Stable and predictable.
    """
    try:
        dt = datetime.fromisoformat(created_at_iso.replace("Z", "+00:00"))
        return dt.strftime("Recording · %Y-%m-%d %H:%M")
    except Exception:
        return "Recording"


def redact_text(text: str, hits) -> str:
    """
    Produce the redacted transcript in a consistent way everywhere.
    Prefers typed labels if supported by the PIIDetector implementation.
    """
    if hasattr(pii, "redact_with_labels"):
        return pii.redact_with_labels(text, hits)
    return pii.redact(text, hits)


def segment_text(text: str, recording_id: str):
    """
    Segment text consistently using SegmentationManager's actual signature.
    """
    # Your SegmentationManager signature:
    # segment(self, transcript, recording_id, method="adaptive")
    return segmenter.segment(transcript=text, recording_id=recording_id)


def first_segment_label(segments) -> Optional[str]:
    """
    Extract a reasonable title from the first segment if available.
    """
    if not segments:
        return None
    first = segments[0]
    label = getattr(first, "label", None) or (first.get("label") if isinstance(first, dict) else None)
    if isinstance(label, str) and label.strip():
        return label.strip()
    return None


# =============================================================================
# Pipelines
# =============================================================================

def process_uploaded_audio(filename: str, file_bytes: bytes, language: str = "en") -> Dict[str, Any]:
    """
    Upload pipeline:
    - Save upload (store rel path)
    - Transcribe
    - Detect PII on original transcript
    - Save original transcript
    - Save redacted transcript (typed labels if supported)
    - Save metadata

    Note: segmentation is NOT done here by default (you can add it later if desired).
    """
    rec_id, audio_rel = store.save_upload(filename, file_bytes)
    audio_abs = store.abs_path(audio_rel)

    rec = Recording(id=rec_id, path=audio_abs, language=language)

    created_at = getattr(rec, "created_at", None) or now_utc_iso()

    # --- Transcription ---
    transcript = transcriber.transcribe(rec)
    if transcript is None or not getattr(transcript, "text", None):
        raise RuntimeError("Transcription failed: no transcript text returned")

    original_text = transcript.text

    # --- PII on original ---
    pii_hits_original = pii.detect(transcript)
    redacted_text_original = redact_text(original_text, pii_hits_original)

    # --- Persist transcripts ---
    original_path = store.save_transcript(rec_id, original_text, version="original")
    redacted_path = store.save_transcript(rec_id, redacted_text_original, version="redacted")

    # --- Metadata ---
    metadata = {
        "recording_id": rec_id,
        "audio": audio_rel,
        "language": language,
        "source": "audio",
        "created_at": created_at,

        "title": fallback_title(created_at),
        "tags": [],

        "transcripts": {
            "original": original_path,
            "edited": None,
            "redacted": redacted_path,
        },
        "segments": [],

        # PII separation (stable meaning)
        "pii_original": [p.__dict__ for p in pii_hits_original],
        "pii_edited": [],

        # Optional convenience field for old UI code; keep it consistent
        # Current PII defaults to original until an edited transcript exists
        "pii": [p.__dict__ for p in pii_hits_original],
    }

    store.save_metadata(rec_id, metadata)

    return {
        "recording_id": rec_id,
        "transcript": {"text": original_text},
        "pii": [p.__dict__ for p in pii_hits_original],
    }


def process_after_edit(recording_id: str, edited_text: str) -> Dict[str, Any]:
    """
    After user edits:
    - Save edited transcript
    - Segment edited text
    - Detect PII on edited text
    - Save redacted transcript for edited text
    - Save segments file
    - Update metadata (keep pii_original intact)
    - Optionally improve title if it is still a fallback/default
    """
    edited_text = (edited_text or "").strip()
    if not edited_text:
        raise RuntimeError("Edited transcript is empty")

    # --- Save edited transcript ---
    edited_path = store.save_transcript(recording_id, edited_text, version="edited")

    # --- Segment edited ---
    segments = segment_text(edited_text, recording_id)
    segments_path = store.save_segments(recording_id, segments)

    # --- PII on edited ---
    edited_transcript_obj = type("Transcript", (), {"recording_id": recording_id, "text": edited_text})
    pii_hits_edited = pii.detect(edited_transcript_obj)

    redacted_text_edited = redact_text(edited_text, pii_hits_edited)
    redacted_path = store.save_transcript(recording_id, redacted_text_edited, version="redacted")

    # --- Update metadata ---
    meta = store.load_metadata(recording_id) or {}
    meta.setdefault("transcripts", {})
    meta.setdefault("segments", [])

    meta["transcripts"]["edited"] = edited_path
    meta["transcripts"]["redacted"] = redacted_path
    meta["segments"] = [segments_path]

    # Preserve original PII if not present
    if "pii_original" not in meta:
        meta["pii_original"] = meta.get("pii", []) or []

    meta["pii_edited"] = [p.__dict__ for p in pii_hits_edited]

    # Keep convenience "pii" as current view (edited preferred)
    meta["pii"] = meta["pii_edited"]

    # Optional: set title from first segment if title looks like fallback
    # Only do this if user hasn't set a custom title.
    cur_title = (meta.get("title") or "").strip()
    if not cur_title or cur_title.startswith("Recording ·"):
        seg_title = first_segment_label(segments)
        if seg_title:
            meta["title"] = seg_title

    store.save_metadata(recording_id, meta)

    return {
        "recording_id": recording_id,
        "segments": [s.__dict__ for s in segments],
        "pii_edited": [p.__dict__ for p in pii_hits_edited],
        "status": "saved",
    }