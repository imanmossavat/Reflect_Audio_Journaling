# app/api/routes.py
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException
)
from app.pipelines.processing import process_uploaded_audio
from app.services.transcription import TranscriptionManager
from app.services.segmentation import SegmentationManager
from app.services.pii import PIIDetector
from app.core.config import settings
import tempfile
import shutil
import logging
import os

router = APIRouter()
logger = logging.getLogger(__name__)

# Instantiate services once (keeps models in memory)
transcriber = TranscriptionManager()
segmenter = SegmentationManager()
pii_detector = PIIDetector()

# ------------------ ROUTES ------------------ #

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
    3. Segment topics
    4. Detect PII
    Returns a structured JSON result.
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        logger.info(f"[UPLOAD] Processing {file.filename} ({language})")

        # Full pipeline (transcribe → segment → pii)
        result = process_uploaded_audio(tmp_path, open(tmp_path, "rb").read(), language)

        os.remove(tmp_path)  # cleanup temp file
        return result

    except Exception as e:
        logger.exception(f"[ERROR] Failed to process file: {file.filename}")
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


@router.get("/settings")
def health_check():
    """
    Return full configuration state (for debugging only).
    """
    return {
        "status": "ok",
        "settings": settings.model_dump(),  # all config fields
    }