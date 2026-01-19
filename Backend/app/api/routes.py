from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException,
    Body,
    Query,
)
from fastapi.responses import FileResponse

from app.pipelines.processing import process_uploaded_audio, process_after_edit
from app.services.transcription import TranscriptionManager
from app.services.segmentation import SegmentationManager
from app.services.storage import StorageManager
from app.services.pii import PIIDetector
from app.core.config import settings
from pydantic import BaseModel
from typing import List, Optional

import tempfile
import shutil
import logging
import os
import json
from pathlib import Path

router = APIRouter()
logger = logging.getLogger(__name__)

transcriber = TranscriptionManager()
segmenter = SegmentationManager()
pii_detector = PIIDetector()
store = StorageManager()

# ------------------ ROUTES ------------------ #


@router.get("/audio/{recording_id}")
async def get_audio(recording_id: str):
    meta = store.load_metadata(recording_id)
    audio_rel = meta.get("audio")

    if not audio_rel:
        raise HTTPException(status_code=404, detail="Audio not found")

    audio_abs = store.abs_path(audio_rel)
    if not os.path.exists(audio_abs):
        raise HTTPException(status_code=404, detail="Audio not found")

    # Optional: try to set a better media_type based on extension
    ext = Path(audio_abs).suffix.lower()
    media_type = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".webm": "audio/webm",
    }.get(ext, "application/octet-stream")

    return FileResponse(audio_abs, media_type=media_type)

def _extract_text_from_transcript_obj(obj) -> str:
    if not obj:
        return ""

    # transcript kan string zijn
    if isinstance(obj, str):
        return obj

    # transcript kan dict zijn
    if isinstance(obj, dict):
        # directe velden
        for k in ("text", "transcript", "content"):
            v = obj.get(k)
            if isinstance(v, str) and v.strip():
                return v

        # Whisper-ish segments
        segs = obj.get("segments")
        if isinstance(segs, list):
            parts = []
            for s in segs:
                if isinstance(s, dict):
                    t = s.get("text") or s.get("sentence") or s.get("content")
                    if isinstance(t, str) and t.strip():
                        parts.append(t.strip())
            if parts:
                return " ".join(parts)

    return ""

def _pick_latest_version(t: dict) -> str | None:
    if not isinstance(t, dict):
        return None
    if t.get("edited"):
        return "edited"
    if t.get("redacted"):
        return "redacted"
    if t.get("original"):
        return "original"
    return None


def _get_transcript_rel_path(recording_id: str, t: dict, version: str) -> str | None:
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

    # if metadata doesn't say anything, still try default path (optional)
    return None

@router.get("/recordings")
async def list_recordings():
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

        # build search_text (truncate to avoid huge payloads)
        search_text = ""
        if latest:
            rel = _get_transcript_rel_path(rec_id, t, latest)
            if rel and store.exists_rel(rel):
                try:
                    search_text = store.load_text(rel) or ""
                except Exception:
                    search_text = ""

        MAX_CHARS = 4000
        if len(search_text) > MAX_CHARS:
            search_text = search_text[:MAX_CHARS]

        # IMPORTANT: expose transcript availability booleans to frontend
        def _has(version: str) -> bool:
            v = t.get(version)
            if isinstance(v, bool):
                return v
            if isinstance(v, str):
                return bool(v.strip()) and store.exists_rel(v)
            return False

        items.append(
            {
                "recording_id": rec_id,
                "title": meta.get("title"),
                "tags": meta.get("tags", []),
                "created_at": meta.get("created_at"),
                "has_audio": bool(meta.get("audio")),
                "transcripts": {
                    "original": _has("original"),
                    "edited": _has("edited"),
                    "redacted": _has("redacted"),
                },
                "latest_transcript_version": latest,
                "search_text": search_text,
            }
        )

    items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return items

@router.post("/recordings/upload")
async def upload_recording(
        file: UploadFile = File(...),
        language: str = Form(settings.LANGUAGE),
):
    """
    Full pipeline endpoint.
    Upload an audio file and process it.
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        logger.info(f"[UPLOAD] Processing {file.filename} ({language})")

        try:
            result = process_uploaded_audio(tmp_path, open(tmp_path, "rb").read(), language)
            os.remove(tmp_path)
            return result
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        logger.exception(f"[ERROR] Failed to process file: {file.filename}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recordings/finalize")
async def finalize_recording(
        recording_id: str = Form(...),
        edited_transcript: str = Form(...),
):
    """
    Final pipeline:
    - User edited transcript
    - Segment
    - Save transcript file
    - Return segments and success message
    """
    try:
        result = process_after_edit(recording_id, edited_transcript)
        return result
    except Exception as e:
        logger.exception("[ERROR] Finalizing recording failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transcriptions")
async def transcribe_audio(
        file: UploadFile = File(...),
        language: str = Form(settings.LANGUAGE),
):
    """
    Upload an audio file and return its transcription only.
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        recording = type("Recording", (), {"id": "temp", "path": tmp_path, "language": language})
        transcript = transcriber.transcribe(recording)

        os.remove(tmp_path)
        return {"text": transcript.text, "words": transcript.words}

    except Exception as e:
        logger.exception(f"[ERROR] Transcription failed for {file.filename}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/segments")
async def segment_text(
        text: str = Form(...),
        recording_id: str = Form("temp"),
):
    """
    Segment an existing transcript into topic-based chunks.
    """
    try:
        transcript = type("Transcript", (), {"recording_id": recording_id, "text": text})
        segments = segmenter.segment(transcript)

        return {"segments": [s.__dict__ for s in segments]}

    except Exception as e:
        logger.exception("[ERROR] Segmentation failed.")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pii")
async def detect_pii(
        text: str = Form(...),
        recording_id: str = Form("temp"),
):
    """
    Detect personally identifiable information (PII) in a given text.
    """
    try:
        transcript = type("Transcript", (), {"recording_id": recording_id, "text": text})
        pii_findings = pii_detector.detect(transcript)

        return {"pii": [p.__dict__ for p in pii_findings], "count": len(pii_findings)}

    except Exception as e:
        logger.exception("[ERROR] PII detection failed.")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recordings/{recording_id}")
async def get_recording(recording_id: str):
    meta = store.load_metadata(recording_id)

    # ---- transcript: prefer edited, fallback original, then redacted ----
    transcript_text = ""
    transcript_version = None

    t = meta.get("transcripts", {}) or {}
    tr_path = t.get("edited") or t.get("original") or t.get("redacted")
    if tr_path:
        transcript_text = store.load_text(tr_path)
        if tr_path == t.get("edited"):
            transcript_version = "edited"
        elif tr_path == t.get("original"):
            transcript_version = "original"
        else:
            transcript_version = "redacted"

    # ---- segments: load the latest saved segments file ----
    segments = []
    seg_paths = meta.get("segments", []) or []
    if seg_paths:
        try:
            payload = store.load_json(seg_paths[-1])
            segments = payload.get("segments", [])
        except Exception:
            segments = []

    return {
        "recording_id": recording_id,
        "audio_url": f"/api/audio/{recording_id}",
        "title": meta.get("title"),
        "tags": meta.get("tags", []),
        "transcript": transcript_text,
        "transcript_version": transcript_version,
        "segments": segments,
        "pii": meta.get("pii", []),
        "pii_original": meta.get("pii_original", meta.get("pii", [])),
        "pii_edited": meta.get("pii_edited", []),
        "created_at": meta.get("created_at"),
        "transcripts": t,
    }

@router.post("/settings/update")
async def update_settings(payload: dict):
    frontend_path = os.path.join(settings.CONFIG_DIR, "frontend_settings.json")
    os.makedirs(settings.CONFIG_DIR, exist_ok=True)

    with open(frontend_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return {"status": "ok", "updated": payload}


@router.get("/settings")
async def get_settings():
    frontend_path = os.path.join(settings.CONFIG_DIR, "frontend_settings.json")

    if os.path.exists(frontend_path):
        with open(frontend_path, "r", encoding="utf-8") as f:
            user_settings = json.load(f)
    else:
        user_settings = {}

    return {
        "status": "ok",
        "settings": {**settings.__dict__, **user_settings},
    }


@router.get("/recordings/{recording_id}/transcript")
async def get_transcript(recording_id: str, version: str = Query("original")):
    meta = store.load_metadata(recording_id)
    transcripts = meta.get("transcripts", {}) or {}
    rel_path = transcripts.get(version)

    if not rel_path:
        return {"recording_id": recording_id, "version": version, "text": ""}

    return {"recording_id": recording_id, "version": version, "text": store.load_text(rel_path)}


@router.put("/recordings/{recording_id}/transcript/edited")
async def save_edited_transcript(recording_id: str, payload: dict = Body(...)):
    edited_text = payload.get("text")
    if not edited_text:
        raise HTTPException(status_code=400, detail="Missing 'text'")

    edited_path = store.save_transcript(recording_id, edited_text, version="edited")

    meta = store.load_metadata(recording_id)
    meta.setdefault("transcripts", {})
    meta["transcripts"]["edited"] = edited_path
    store.save_metadata(recording_id, meta)

    return {"status": "ok", "recording_id": recording_id, "edited_path": edited_path}


@router.delete("/recordings/{recording_id}/transcript")
async def delete_transcript(recording_id: str, version: str = Query("all")):
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


@router.delete("/recordings/{recording_id}/audio")
async def delete_audio(recording_id: str):
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


@router.delete("/recordings/{recording_id}/segments")
async def delete_segments(recording_id: str):
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

@router.delete("/recordings/{recording_id}")
async def delete_recording(recording_id: str):
    try:
        store.delete_recording(recording_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Recording not found")

    return {
        "status": "ok",
        "recording_id": recording_id,
        "deleted": True
    }

class UpdateMetaPayload(BaseModel):
    title: Optional[str] = None
    tags: Optional[List[str]] = None

@router.patch("/recordings/{recording_id}/meta")
async def update_recording_meta(recording_id: str, payload: UpdateMetaPayload):
    meta = store.load_metadata(recording_id)

    if payload.title is not None:
        meta["title"] = payload.title.strip()

    if payload.tags is not None:
        # normalize tags: trim, drop empties, unique
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


