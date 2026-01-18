from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException,
    Body, 
    Query
)
from fastapi.responses import FileResponse

from app.pipelines.processing import process_uploaded_audio, process_after_edit
from app.services.transcription import TranscriptionManager
from app.services.segmentation import SegmentationManager
from app.services.storage import StorageManager
from app.services.pii import PIIDetector
from app.core.config import settings
import tempfile
import shutil
import logging
import os
import json

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
    audio_path = meta.get("audio")

    if not audio_path or not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio not found")

    return FileResponse(audio_path, media_type="audio/wav")


@router.get("/recordings")
async def list_recordings():
    items = []
    for meta_file in os.listdir(os.path.join(settings.DATA_DIR, "metadata")):
        if meta_file.endswith(".json"):
            rec_id = meta_file.replace(".json", "")
            meta = store.load_metadata(rec_id)
            items.append({
                "recording_id": rec_id,
                "created_at": meta.get("created_at"),
                "audio": meta.get("audio"),
                "latest_transcript": meta.get("latest_transcript"),
            })
    return items

@router.post("/recordings/upload")
async def upload_recording(
    file: UploadFile = File(...),
    language: str = Form(settings.LANGUAGE)
):
    """
    Full pipeline endpoint.
    Upload an audio file and process it:
    1. Save file
    2. Transcribe
    3. Detect PII
    4. Edit transcript
    5. Save transcript

    Returns a structured JSON result.
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
    edited_transcript: str = Form(...)
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
    language: str = Form(settings.LANGUAGE)
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
    recording_id: str = Form("temp")
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
    recording_id: str = Form("temp")
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
        # figure out which one we used
        if tr_path == t.get("edited"):
            transcript_version = "edited"
        elif tr_path == t.get("original"):
            transcript_version = "original"
        else:
            transcript_version = "redacted"

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
        "transcript": transcript_text,
        "transcript_version": transcript_version,
        "segments": segments,
        "pii": meta.get("pii", []),
        "created_at": meta.get("created_at"),
        "transcripts": t,
    }


@router.post("/settings/update")
async def update_settings(payload: dict):
    frontend_path = os.path.join(settings.CONFIG_DIR, "frontend_settings.json")
    os.makedirs(settings.CONFIG_DIR, exist_ok=True)

    with open(frontend_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

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
        "settings": {
            **settings.__dict__,   # backend defaults
            **user_settings        # overrides
        }
    }

@router.get("/recordings/{recording_id}/transcript")
async def get_transcript(recording_id: str, version: str = Query("original")):
    meta = store.load_metadata(recording_id)
    transcripts = meta.get("transcripts", {})
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
    # versions: original, edited, redacted, all
    meta = store.load_metadata(recording_id)
    meta.setdefault("transcripts", {})

    versions = ["original", "edited", "redacted"] if version == "all" else [version]
    deleted = []

    for v in versions:
        rel = meta["transcripts"].get(v)
        if not rel:
            continue
        abs_path = os.path.join(settings.DATA_DIR, rel)
        if os.path.exists(abs_path):
            os.remove(abs_path)
        meta["transcripts"][v] = None
        deleted.append(v)

    store.save_metadata(recording_id, meta)
    return {"status": "ok", "recording_id": recording_id, "deleted": deleted}


@router.delete("/recordings/{recording_id}/audio")
async def delete_audio(recording_id: str):
    meta = store.load_metadata(recording_id)
    audio_path = meta.get("audio")
    if not audio_path:
        return {"status": "ok", "recording_id": recording_id, "deleted": False}

    if os.path.exists(audio_path):
        os.remove(audio_path)

    meta["audio"] = None
    store.save_metadata(recording_id, meta)
    return {"status": "ok", "recording_id": recording_id, "deleted": True}

@router.delete("/recordings/{recording_id}/segments")
async def delete_segments(recording_id: str):
    meta = store.load_metadata(recording_id)
    seg_paths = meta.get("segments", []) or []

    deleted = 0
    for rel in seg_paths:
        abs_path = os.path.join(settings.DATA_DIR, rel)
        if os.path.exists(abs_path):
            os.remove(abs_path)
            deleted += 1

    meta["segments"] = []
    store.save_metadata(recording_id, meta)

    return {"status": "ok", "recording_id": recording_id, "deleted_count": deleted}

@router.delete("/recordings/{recording_id}")
async def delete_recording(recording_id: str):
    meta = store.load_metadata(recording_id)

    # delete audio
    ap = meta.get("audio")
    if ap and os.path.exists(ap):
        os.remove(ap)

    # delete transcripts
    for rel in (meta.get("transcripts") or {}).values():
        if rel:
            abs_path = os.path.join(settings.DATA_DIR, rel)
            if os.path.exists(abs_path):
                os.remove(abs_path)

    # delete segments
    for rel in meta.get("segments", []):
        try:
            abs_path = os.path.join(settings.DATA_DIR, rel)
            if os.path.exists(abs_path):
                os.remove(abs_path)
        except:
            pass

    # delete metadata file
    meta_file = os.path.join(settings.DATA_DIR, "metadata", f"{recording_id}.json")
    if os.path.exists(meta_file):
        os.remove(meta_file)

    return {"status": "ok", "recording_id": recording_id, "deleted": True}
