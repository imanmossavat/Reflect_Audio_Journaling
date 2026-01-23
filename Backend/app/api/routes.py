from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Body, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.core.config import settings
from app.pipelines.processing import process_after_edit, process_uploaded_audio
from app.services.pii import PIIDetector
from app.services.segmentation import SegmentationManager
from app.services.storage import StorageManager
from app.services.transcription import TranscriptionManager
from app.services.semantic_search import SemanticSearchManager
from app.services.settings import SettingsManager
from app.services.recordings import RecordingService
from app.domain.models import PiiFinding
from app.api.schemas import (
    SettingsUpdatePayload, UpdateMetaPayload, SaveTranscriptPayload,
    CreateTextRecordingPayload, SemanticSearchPayload, UpdatePIIPayload, OpenFolderPayload
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize managers
store = StorageManager()
transcriber = TranscriptionManager()
segmenter = SegmentationManager()
pii_detector = PIIDetector()
semanticSearcher = SemanticSearchManager()
settings_manager = SettingsManager()
recording_service = RecordingService(store)

AUDIO_MEDIA_TYPES = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".webm": "audio/webm",
}

# =============================================================================
# Settings
# =============================================================================

@router.get("/settings", tags=["Settings"])
async def get_settings():
    return {"status": "ok", "settings": settings_manager.get_effective_settings()}

@router.post("/settings/update", tags=["Settings"])
async def update_settings(payload: dict = Body(...)):
    result = settings_manager.update_settings(payload)
    if result.get("status") == "error":
        return result
    return result

@router.post("/settings/reset", tags=["Settings"])
async def reset_settings():
    if settings_manager.reset_settings():
        return {"status": "ok", "message": "Overrides deleted. Restart required to fully revert."}
    return {"status": "ok", "message": "No overrides found."}

@router.post("/settings/open-folder", tags=["Settings"])
async def open_folder(payload: dict = Body(...)):
    path = payload.get("path")
    success, error = settings_manager.open_folder(path)
    if not success:
        raise HTTPException(status_code=404 if error == "Path not found" else 500, detail=error)
    return {"status": "ok"}


# =============================================================================
# Recordings (library + CRUD)
# =============================================================================

@router.get("/recordings", tags=["Recordings"])
async def list_recordings():
    return recording_service.list_recordings()

@router.get("/recordings/{recording_id}", tags=["Recordings"])
async def get_recording(recording_id: str):
    data = recording_service.get_recording_full(recording_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Recording {recording_id} not found")
    return data


@router.patch("/recordings/{recording_id}/meta", tags=["Recordings"])
async def update_recording_meta(recording_id: str, payload: UpdateMetaPayload):
    try:
        meta = store.load_metadata(recording_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Recording not found")

    if payload.title is not None:
        meta["title"] = payload.title.strip()

    if payload.tags is not None:
        cleaned = list(dict.fromkeys(t.strip() for t in payload.tags if t and t.strip()))
        meta["tags"] = cleaned

    store.save_metadata(recording_id, meta)
    return {"status": "ok", "recording_id": recording_id, "title": meta.get("title"), "tags": meta.get("tags", [])}

@router.delete("/recordings/{recording_id}", tags=["Recordings"])
async def delete_recording(recording_id: str):
    try:
        store.delete_recording(recording_id)
        return {"status": "ok", "recording_id": recording_id, "deleted": True}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Recording not found")

# =============================================================================
# Audio
# =============================================================================

@router.get("/audio/{recording_id}", tags=["Audio"])
async def get_audio(recording_id: str):
    try:
        meta = store.load_metadata(recording_id)
        audio_rel = meta.get("audio")
        if not audio_rel:
            raise HTTPException(status_code=404, detail="Audio not found")

        audio_abs = store.abs_path(audio_rel)
        if not os.path.exists(audio_abs):
            raise HTTPException(status_code=404, detail="Audio file missing from disk")

        ext = Path(audio_abs).suffix.lower()
        media_type = AUDIO_MEDIA_TYPES.get(ext, "application/octet-stream")
        return FileResponse(audio_abs, media_type=media_type)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Recording not found")

@router.delete("/recordings/{recording_id}/audio", tags=["Audio"])
async def delete_audio(recording_id: str):
    try:
        if store.delete_audio(recording_id):
            return {"status": "ok", "recording_id": recording_id, "deleted": True}
        return {"status": "ok", "recording_id": recording_id, "deleted": False}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Recording not found")

# =============================================================================
# Transcripts
# =============================================================================

@router.get("/recordings/{recording_id}/transcript", tags=["Transcripts"])
async def get_transcript(recording_id: str, version: str = Query("original")):
    try:
        meta = store.load_metadata(recording_id)
        t_meta = meta.get("transcripts", {}) or {}
        rel_path = t_meta.get(version)
        
        if not rel_path or not store.exists_rel(rel_path):
            return {"recording_id": recording_id, "version": version, "text": ""}
            
        return {"recording_id": recording_id, "version": version, "text": store.load_text(rel_path)}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Recording not found")


@router.put("/recordings/{recording_id}/transcript/edited", tags=["Transcripts"])
async def save_edited_transcript(recording_id: str, payload: SaveTranscriptPayload = Body(...)):
    edited_text = payload.text.strip()
    if not edited_text:
        raise HTTPException(status_code=400, detail="Missing 'text'")

    edited_path = store.save_transcript(recording_id, edited_text, version="edited")

    try:
        meta = store.load_metadata(recording_id)
        meta.setdefault("transcripts", {})
        meta["transcripts"]["edited"] = edited_path
        store.save_metadata(recording_id, meta)
        return {"status": "ok", "recording_id": recording_id, "edited_path": edited_path}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Recording not found")

@router.delete("/recordings/{recording_id}/transcript", tags=["Transcripts"])
async def delete_transcript(recording_id: str, version: str = Query("all")):
    try:
        meta = store.load_metadata(recording_id)
        versions = ["original", "edited", "redacted"] if version == "all" else [version]
        deleted = []
        for v in versions:
            if store.delete_transcript(recording_id, v):
                deleted.append(v)
        return {"status": "ok", "recording_id": recording_id, "deleted": deleted}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Recording not found")


# =============================================================================
# Processing Pipelines
# =============================================================================

@router.post("/recordings/upload", tags=["Processing"])
async def upload_recording(file: UploadFile = File(...), language: str = Form(settings.LANGUAGE)):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        try:
            result = process_uploaded_audio(tmp_path, open(tmp_path, "rb").read(), language)
            os.remove(tmp_path)
            return result
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"[ERROR] Failed to process file: {file.filename}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/recordings/finalize", tags=["Processing"])
async def finalize_recording(recording_id: str = Form(...), edited_transcript: str = Form(...)):
    try:
        return process_after_edit(recording_id, edited_transcript)
    except Exception as e:
        logger.exception("[ERROR] Finalizing recording failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recordings/text", tags=["Processing"])
async def create_text_recording(payload: CreateTextRecordingPayload):
    try:
        from app.pipelines.processing import process_text_entry
        return process_text_entry(
            text=payload.text,
            title=payload.title,
            tags=payload.tags,
            language=payload.language,
            run_segmentation=payload.run_segmentation,
            run_pii=payload.run_pii
        )
    except Exception as e:
        logger.exception("Text entry processing failed")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# AI Tools (Stateless)
# =============================================================================

@router.post("/transcriptions", tags=["AI Tools"])
async def transcribe_audio(file: UploadFile = File(...), language: str = Form(settings.LANGUAGE)):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        recording = type("R", (), {"id": "temp", "path": tmp_path, "language": language})
        transcript = transcriber.transcribe(recording)
        os.remove(tmp_path)
        return {"text": transcript.text, "words": transcript.words, "sentences": transcript.sentences}
    except Exception as e:
        logger.exception(f"[ERROR] Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/semantic", tags=["AI Tools"])
async def semantic_search(payload: SemanticSearchPayload):
    try:
        hits = semanticSearcher.search(
            query=payload.query, 
            top_k=payload.top_k, 
            min_score=payload.min_score,
            per_recording_cap=payload.per_recording_cap
        )
        return {"hits": [h.__dict__ for h in hits]}
    except Exception as e:
        logger.exception(f"Semantic search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/recordings/{recording_id}/pii", tags=["Recordings"])
async def sync_pii(recording_id: str, payload: UpdatePIIPayload):
    try:
        meta = store.load_metadata(recording_id)
        findings_dicts = [f.dict() if hasattr(f, 'dict') else f.__dict__ for f in payload.findings]
        meta["pii"] = findings_dicts
        meta["pii_edited"] = findings_dicts
        store.save_metadata(recording_id, meta)
        return {"status": "ok"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Recording not found")

@router.post("/pii", tags=["AI Tools"])
async def detect_pii(text: str = Form(...), recording_id: str = Form("temp")):
    try:
        hits = pii_detector.detect(type("T", (), {"recording_id": recording_id, "text": text}))
        return {"pii": [p.__dict__ for p in hits], "count": len(hits)}
    except Exception as e:
        logger.exception("PII detection failed")
        raise HTTPException(status_code=500, detail=str(e))