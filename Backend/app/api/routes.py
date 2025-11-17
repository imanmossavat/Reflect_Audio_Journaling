from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException
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

        result = process_uploaded_audio(tmp_path, open(tmp_path, "rb").read(), language)

        os.remove(tmp_path)
        return result

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

    transcript_text = ""
    tr_path = meta.get("latest_transcript")
    if tr_path:
        transcript_text = store.load_text(tr_path)

    segments = []
    for seg_path in meta.get("segments", []):
        try:
            segments.append(store.load_json(seg_path))
        except:
            pass

    return {
        "recording_id": recording_id,
        "audio_url": f"/api/audio/{recording_id}",
        "transcript": transcript_text,
        "segments": segments,
        "pii": meta.get("pii", []),
        "created_at": meta.get("created_at"),
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