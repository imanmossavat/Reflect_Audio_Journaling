from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Body, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from datetime import datetime
import uuid
from pydantic import BaseModel, Field

from app.core.config import settings
from app.pipelines.processing import process_after_edit, process_uploaded_audio
from app.services.pii import PIIDetector
from app.services.segmentation import SegmentationManager
from app.services.storage import StorageManager
from app.services.transcription import TranscriptionManager
from app.services.semanticSearch import SemanticSearchManager

router = APIRouter()
logger = logging.getLogger(__name__)

transcriber = TranscriptionManager()
segmenter = SegmentationManager()
pii_detector = PIIDetector()
store = StorageManager()
semanticSearcher = SemanticSearchManager()

# =============================================================================
# Helpers (internal)
# =============================================================================

AUDIO_MEDIA_TYPES = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".webm": "audio/webm",
}


def _pick_latest_version(t: dict) -> Optional[str]:
    """Pick the most relevant transcript version, in order of preference."""
    if not isinstance(t, dict):
        return None
    if t.get("edited"):
        return "edited"
    if t.get("redacted"):
        return "redacted"
    if t.get("original"):
        return "original"
    return None


def _get_transcript_rel_path(recording_id: str, t: dict, version: str) -> Optional[str]:
    """
    Supports both metadata styles:
    - transcripts[version] is a rel path (preferred)
    - transcripts[version] is a boolean, then use default path
    """
    if not version:
        return None

    val = (t or {}).get(version)

    # preferred: rel path stored in metadata
    if isinstance(val, str) and val.strip():
        return val

    # legacy/boolean: transcript exists => use default path used by save_transcript()
    if val is True:
        return f"transcripts/{recording_id}/{version}.txt"

    return None


def _safe_load_text(rel_path: Optional[str]) -> str:
    if not rel_path:
        return ""
    if not store.exists_rel(rel_path):
        return ""
    try:
        return store.load_text(rel_path) or ""
    except Exception:
        return ""


def _has_transcript(t: dict, version: str) -> bool:
    """Expose transcript availability to frontend, supports bool or path style."""
    v = (t or {}).get(version)
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return bool(v.strip()) and store.exists_rel(v)
    return False


# =============================================================================
# Settings
# =============================================================================

class SettingsUpdatePayload(BaseModel):
    """Settings payload stored to frontend_settings.json (merged with backend defaults)."""
    # keep it flexible on purpose, but still validated as a dict
    settings: dict = Field(default_factory=dict)


@router.get("/settings", tags=["Settings"])
async def get_settings():
    """
    Get effective settings for the frontend.

    Returns:
    - backend defaults (from app.core.config.settings)
    - merged with user overrides from config/frontend_settings.json
    """
    frontend_path = os.path.join(settings.CONFIG_DIR, "frontend_settings.json")

    if os.path.exists(frontend_path):
        with open(frontend_path, "r", encoding="utf-8") as f:
            user_settings = json.load(f)
    else:
        user_settings = {}

    return {"status": "ok", "settings": {**settings.__dict__, **user_settings}}


@router.post("/settings/update", tags=["Settings"])
async def update_settings(payload: dict = Body(...)):
    """
    Update frontend-visible settings overrides.

    Stores payload as JSON in:
    config/frontend_settings.json
    """
    frontend_path = os.path.join(settings.CONFIG_DIR, "frontend_settings.json")
    os.makedirs(settings.CONFIG_DIR, exist_ok=True)

    with open(frontend_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return {"status": "ok", "updated": payload}


# =============================================================================
# Recordings (library + CRUD)
# =============================================================================

@router.get("/recordings", tags=["Recordings"])
async def list_recordings():
    """
    List recordings for the library view.

    Returns lightweight objects including:
    - transcript availability flags (original/edited/redacted)
    - latest_transcript_version
    - search_text preview (truncated)
    """
    items = []
    meta_dir = os.path.join(settings.DATA_DIR, "metadata")

    if not os.path.isdir(meta_dir):
        return []

    for meta_file in os.listdir(meta_dir):
        if not meta_file.endswith(".json"):
            continue

        rec_id = meta_file[:-5]

        try:
            meta = store.load_metadata(rec_id) or {}
        except FileNotFoundError:
            continue

        t = meta.get("transcripts", {}) or {}
        latest = _pick_latest_version(t)

        # Build search_text preview (truncate to avoid huge payloads)
        search_text = ""
        if latest:
            rel = _get_transcript_rel_path(rec_id, t, latest)
            search_text = _safe_load_text(rel)

        MAX_CHARS = 4000
        if len(search_text) > MAX_CHARS:
            search_text = search_text[:MAX_CHARS]

        items.append(
            {
                "recording_id": rec_id,
                "title": meta.get("title"),
                "tags": meta.get("tags", []),
                "created_at": meta.get("created_at"),
                "has_audio": bool(meta.get("audio")),
                "transcripts": {
                    "original": _has_transcript(t, "original"),
                    "edited": _has_transcript(t, "edited"),
                    "redacted": _has_transcript(t, "redacted"),
                },
                "latest_transcript_version": latest,
                "search_text": search_text,
            }
        )

    items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return items


@router.get("/recordings/{recording_id}", tags=["Recordings"])
async def get_recording(recording_id: str):
    """
    Get a recording with transcript + latest segments.

    Transcript selection order:
    edited -> original -> redacted
    """
    meta = store.load_metadata(recording_id)

    # ---- transcript: prefer edited, fallback original, then redacted ----
    t = meta.get("transcripts", {}) or {}
    chosen_version = "edited" if t.get("edited") else ("original" if t.get("original") else ("redacted" if t.get("redacted") else None))

    transcript_text = ""
    transcript_version = None
    if chosen_version:
        rel = _get_transcript_rel_path(recording_id, t, chosen_version)
        transcript_text = _safe_load_text(rel)
        transcript_version = chosen_version

    # ---- segments: load the latest saved segments file ----
    segments = []
    seg_paths = meta.get("segments", []) or []
    if seg_paths:
        try:
            payload = store.load_json(seg_paths[-1])
            segments = payload.get("segments", [])
        except Exception:
            segments = []

    aligned_words = []
    rel = meta.get("aligned_words")
    if rel and store.exists_rel(rel):
        aligned_words = store.load_json(rel)

    return {
        "recording_id": recording_id,
        "audio_url": f"/api/audio/{recording_id}",
        "title": meta.get("title"),
        "tags": meta.get("tags", []),
        "transcript": transcript_text,
        "transcript_version": transcript_version,
        "prosody": meta.get("prosody", []),
        "aligned_words": aligned_words,
        "segments": segments,
        "pii": meta.get("pii", []),
        "pii_original": meta.get("pii_original", meta.get("pii", [])),
        "pii_edited": meta.get("pii_edited", []),
        "created_at": meta.get("created_at"),
        "transcripts": t,
        "has_audio": bool(meta.get("audio")),
        "sentences": meta.get("sentences", []),
        "speech": meta.get("speech", {})
    }


class UpdateMetaPayload(BaseModel):
    title: Optional[str] = None
    tags: Optional[List[str]] = None


@router.patch("/recordings/{recording_id}/meta", tags=["Recordings"])
async def update_recording_meta(recording_id: str, payload: UpdateMetaPayload):
    """
    Update recording metadata (title/tags).
    Tags are normalized:
    - trimmed
    - empty values dropped
    - unique (case-insensitive)
    """
    meta = store.load_metadata(recording_id)

    if payload.title is not None:
        meta["title"] = payload.title.strip()

    if payload.tags is not None:
        cleaned = []
        seen = set()
        for t in payload.tags:
            t2 = (t or "").strip()
            if not t2:
                continue
            key = t2.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(t2)
        meta["tags"] = cleaned

    store.save_metadata(recording_id, meta)
    return {"status": "ok", "recording_id": recording_id, "title": meta.get("title"), "tags": meta.get("tags", [])}


@router.delete("/recordings/{recording_id}", tags=["Recordings"])
async def delete_recording(recording_id: str):
    """
    Delete an entire recording (metadata + audio + transcripts + derived artifacts).
    """
    try:
        store.delete_recording(recording_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Recording not found")

    return {"status": "ok", "recording_id": recording_id, "deleted": True}


# =============================================================================
# Audio (serve + delete)
# =============================================================================

@router.get("/audio/{recording_id}", tags=["Audio"])
async def get_audio(recording_id: str):
    """
    Stream the stored audio file for a recording.
    """
    meta = store.load_metadata(recording_id)
    audio_rel = meta.get("audio")

    if not audio_rel:
        raise HTTPException(status_code=404, detail="Audio not found")

    audio_abs = store.abs_path(audio_rel)
    if not os.path.exists(audio_abs):
        raise HTTPException(status_code=404, detail="Audio not found")

    ext = Path(audio_abs).suffix.lower()
    media_type = AUDIO_MEDIA_TYPES.get(ext, "application/octet-stream")
    return FileResponse(audio_abs, media_type=media_type)


@router.delete("/recordings/{recording_id}/audio", tags=["Audio"])
async def delete_audio(recording_id: str):
    """
    Delete the stored audio file for a recording (metadata stays).
    """
    meta = store.load_metadata(recording_id)
    audio_rel = meta.get("audio")
    if not audio_rel:
        return {"status": "ok", "recording_id": recording_id, "deleted": False}

    audio_abs = store.abs_path(audio_rel)
    if os.path.exists(audio_abs):
        os.remove(audio_abs)

    meta["audio"] = None
    store.save_metadata(recording_id, meta)
    return {"status": "ok", "recording_id": recording_id, "deleted": True}


# =============================================================================
# Transcripts (get/save/delete)
# =============================================================================

@router.get("/recordings/{recording_id}/transcript", tags=["Transcripts"])
async def get_transcript(recording_id: str, version: str = Query("original")):
    """
    Fetch a transcript version for a recording.

    version: original | edited | redacted
    Returns empty text if not available.
    """
    meta = store.load_metadata(recording_id)
    t = meta.get("transcripts", {}) or {}

    rel = _get_transcript_rel_path(recording_id, t, version)
    return {"recording_id": recording_id, "version": version, "text": _safe_load_text(rel)}


class SaveTranscriptPayload(BaseModel):
    text: str = Field(min_length=1)


@router.put("/recordings/{recording_id}/transcript/edited", tags=["Transcripts"])
async def save_edited_transcript(recording_id: str, payload: SaveTranscriptPayload = Body(...)):
    """
    Save edited transcript text for a recording.
    """
    edited_text = payload.text.strip()
    if not edited_text:
        raise HTTPException(status_code=400, detail="Missing 'text'")

    edited_path = store.save_transcript(recording_id, edited_text, version="edited")

    meta = store.load_metadata(recording_id)
    meta.setdefault("transcripts", {})
    meta["transcripts"]["edited"] = edited_path
    store.save_metadata(recording_id, meta)

    return {"status": "ok", "recording_id": recording_id, "edited_path": edited_path}


@router.delete("/recordings/{recording_id}/transcript", tags=["Transcripts"])
async def delete_transcript(recording_id: str, version: str = Query("all")):
    """
    Delete transcript files for a recording.

    version:
    - "all" (default) deletes original/edited/redacted
    - or a specific version: original | edited | redacted
    """
    meta = store.load_metadata(recording_id)
    meta.setdefault("transcripts", {})

    versions = ["original", "edited", "redacted"] if version == "all" else [version]
    deleted = []

    for v in versions:
        rel = meta["transcripts"].get(v)
        if not rel:
            continue

        abs_path = store.abs_path(rel)
        if os.path.exists(abs_path):
            os.remove(abs_path)

        meta["transcripts"][v] = None
        deleted.append(v)

    store.save_metadata(recording_id, meta)
    return {"status": "ok", "recording_id": recording_id, "deleted": deleted}


# =============================================================================
# Derived artifacts (segments)
# =============================================================================

@router.delete("/recordings/{recording_id}/segments", tags=["Recordings"])
async def delete_segments(recording_id: str):
    """
    Delete all saved segment JSON files for a recording.
    """
    meta = store.load_metadata(recording_id)
    seg_paths = meta.get("segments", []) or []

    deleted = 0
    for rel in seg_paths:
        abs_path = store.abs_path(rel)
        if os.path.exists(abs_path):
            os.remove(abs_path)
            deleted += 1

    meta["segments"] = []
    store.save_metadata(recording_id, meta)
    return {"status": "ok", "recording_id": recording_id, "deleted_count": deleted}


# =============================================================================
# Processing pipelines (audio -> transcript -> artifacts)
# =============================================================================

@router.post("/recordings/upload", tags=["Processing"])
async def upload_recording(
    file: UploadFile = File(...),
    language: str = Form(settings.LANGUAGE),
):
    """
    Full pipeline endpoint.

    Upload an audio file and process it (store audio, create metadata, create transcript, etc.).
    Returns a payload including recording_id.
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        logger.info(f"[UPLOAD] Processing {file.filename} ({language})")

        try:
            # Note: process_uploaded_audio currently wants both tmp_path and bytes.
            # This is a bit redundant, but left as-is for now.
            result = process_uploaded_audio(tmp_path, open(tmp_path, "rb").read(), language)
            os.remove(tmp_path)
            return result
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        logger.exception(f"[ERROR] Failed to process file: {file.filename}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recordings/finalize", tags=["Processing"])
async def finalize_recording(
    recording_id: str = Form(...),
    edited_transcript: str = Form(...),
):
    """
    Final pipeline step after user edits transcript.

    - Save edited transcript
    - Re-run segmentation (and anything else in process_after_edit)
    - Return updated artifacts
    """
    try:
        return process_after_edit(recording_id, edited_transcript)
    except Exception as e:
        logger.exception("[ERROR] Finalizing recording failed")
        raise HTTPException(status_code=500, detail=str(e))

class CreateTextRecordingPayload(BaseModel):
    text: str = Field(min_length=1)
    title: Optional[str] = None
    tags: Optional[List[str]] = None
    language: str = settings.LANGUAGE
    run_segmentation: bool = True
    run_pii: bool = True


def _new_recording_id() -> str:
    return uuid.uuid4().hex


@router.post("/recordings/text", tags=["Processing"])
async def create_text_recording(payload: CreateTextRecordingPayload):
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text is empty")

    recording_id = _new_recording_id()
    original_path = store.save_transcript(recording_id, text, version="original")

    meta = {
        "recording_id": recording_id,
        "created_at": datetime.utcnow().isoformat(),
        "title": (payload.title or "").strip() or None,
        "tags": payload.tags or [],
        "language": payload.language,
        "source": "text",
        "audio": None,
        "transcripts": {"original": original_path, "edited": None, "redacted": None},
        "segments": [],
        "pii": [],
        "pii_original": [],
        "pii_edited": [],
    }

    if payload.run_segmentation:
        try:
            import re

            raw_sentences = [
                s.strip()
                for s in re.split(r"(?<=[.!?])\s+", text.strip())
                if s.strip()
            ]

            fake_transcript = type(
                "Transcript",
                (),
                {
                    "recording_id": recording_id,
                    "text": text,
                    "sentences": [
                        {"id": i, "start_s": None, "end_s": None, "text": s}
                        for i, s in enumerate(raw_sentences)
                    ],
                },
            )

            segs = segmenter.segment(transcript=fake_transcript, recording_id=recording_id)

            if not meta.get("title") and segs:
                meta["title"] = (segs[0].label or "").strip() or None

            segments_path = store.save_segments(recording_id, segs)
            meta["segments"] = [segments_path]

        except Exception:
            logger.exception("Segmentation failed for text recording")

    if payload.run_pii:
        try:
            transcript_obj = type("Transcript", (), {"recording_id": recording_id, "text": text})
            hits = pii_detector.detect(transcript_obj)
            meta["pii"] = [p.__dict__ for p in hits]
            meta["pii_original"] = meta["pii"]
        except Exception:
            logger.exception("PII detection failed for text recording")

    store.save_metadata(recording_id, meta)
    return {"status": "ok", "recording_id": recording_id}


# =============================================================================
# AI tools (stateless utilities)
# =============================================================================

@router.post("/transcriptions", tags=["AI Tools"])
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Form(settings.LANGUAGE),
):
    """
    Transcribe an uploaded audio file WITHOUT storing it.

    Useful for debugging or experimentation.
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        recording = type("Recording", (), {"id": "temp", "path": tmp_path, "language": language})
        transcript = transcriber.transcribe(recording)

        os.remove(tmp_path)
        return {
            "text": transcript.text,
            "words": transcript.words,
            "sentences": transcript.sentences
        }
    except Exception as e:
        logger.exception(f"[ERROR] Transcription failed for {file.filename}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/segments", tags=["AI Tools"])
async def segment_text(
        text: str = Form(...),
        recording_id: str = Form("temp"),
        method: str = Form("adaptive"),
):
    """
    Segment a given text WITHOUT storing it.
    """
    try:
        if not text.strip():
            raise HTTPException(status_code=400, detail="Text is empty")

        import re

        raw_sentences = [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+", text.strip())
            if s.strip()
        ]

        fake_transcript = type(
            "Transcript",
            (),
            {
                "recording_id": recording_id,
                "text": text,
                "sentences": [
                    {
                        "id": i,
                        "start_s": None,
                        "end_s": None,
                        "text": s,
                    }
                    for i, s in enumerate(raw_sentences)
                ],
            },
        )

        segments = segmenter.segment(
            transcript=fake_transcript,
            recording_id=recording_id,
            method=method,
        )

        return {"segments": [s.__dict__ for s in segments]}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[ERROR] Segmentation failed.")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pii", tags=["AI Tools"])
async def detect_pii(
    text: str = Form(...),
    recording_id: str = Form("temp")
):
    """
    Detect personally identifiable information (PII) in a given text WITHOUT storing it.
    """
    try:
        transcript = type("Transcript", (), {"recording_id": recording_id, "text": text})
        pii_findings = pii_detector.detect(transcript)
        return {"pii": [p.__dict__ for p in pii_findings], "count": len(pii_findings)}
    except Exception as e:
        logger.exception("[ERROR] PII detection failed.")
        raise HTTPException(status_code=500, detail=str(e))

class SemanticSearchPayload(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = 8
    min_score: float = 0.25
    per_recording_cap: int = 2

@router.post("/search/semantic", tags=["AI Tools"])
async def semantic_search(payload: SemanticSearchPayload):
    try:
        hits = semanticSearcher.search(
            query=payload.query,
            top_k=payload.top_k,
            min_score=payload.min_score,
            per_recording_cap=payload.per_recording_cap,
        )
        return {"hits": [h.__dict__ for h in hits]}
    except Exception as e:
        logger.exception("[ERROR] Semantic search failed.")
        raise HTTPException(status_code=500, detail=str(e))