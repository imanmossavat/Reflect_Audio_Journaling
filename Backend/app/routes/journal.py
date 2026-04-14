from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlmodel import Session

from app.db import get_session
from app.schemas.journalSchemas import SourcePatchRequest
from app.services import journalService

import os

router = APIRouter()

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a",".txt", ".md"}
ALLOWED_MIME_TYPES = {"audio/mpeg", "audio/wav", "text/plain", "text/markdown"}

@router.get("/sources", tags=["Source"])
async def get_all_sources(
    session: Session = Depends(get_session),
):
    return journalService.get_all_sources(session)

@router.get("/unprocessed-sources", tags=["Source"])
async def get_unprocessed_sources(
    session: Session = Depends(get_session),
):
    return journalService.get_unprocessed_sources(session)

@router.get("/source/{source_id}", tags=["Source"])
async def get_source_by_id(
    source_id: int,
    session: Session = Depends(get_session),
):
    return journalService.get_source_by_id(session, source_id)


@router.get("/source-text/{source_id}", tags=["Source"])
async def get_source_text(
    source_id: int,
    session: Session = Depends(get_session),
):
    source = journalService.get_source_by_id(session, source_id)
    return source.text


@router.post("/source/uploadFile/processed", tags=["Source"], description="Upload a source file that will be processed immediately. Transcription is performed if the file is an audio file. Only supports: .wav, .mp3, .txt and .md files.")
async def upload_source(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    extension = os.path.splitext(file.filename)[1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type. Only .wav, .mp3, .txt and .md files are supported.")
    return await journalService.save_processed_source_file(session, file)


@router.post("/source/uploadFile/raw", tags=["Source"], description="Upload a source file that will be processed later. Transcription is performed if the file is an audio file. Only supports: .wav, .mp3, .txt and .md files.")
async def upload_raw_source(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    extension = os.path.splitext(file.filename)[1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file extension type.")
    return await journalService.save_raw_source_file(session, file)

@router.post("/source/uploadText/processed", tags=["Source"], description="Upload a source as text. The source will be processed immediately.")
async def upload_text_source(
    source_text: str = Form(...),
    session: Session = Depends(get_session),
):
    return await journalService.save_processed_source_text(session, source_text)


@router.post("/source/uploadText/raw", tags=["Source"], description="Upload a source as raw text. The source will be processed immediately.")
async def upload_raw_text_source(
    source_text: str = Form(...),
    session: Session = Depends(get_session),
):
    return await journalService.save_raw_source_text(session, source_text)


@router.post("/source/transcribe/{source_id}", tags=["Source"], description="Transcribe an audio source by its ID. This endpoint only performs transcription and stores editable transcript text.")
async def transcribe_source(
    source_id: int,
    session: Session = Depends(get_session),
):
    return await journalService.transcribe_source(session, source_id)


@router.patch("/source/{source_id}", tags=["Source"], description="Update a source transcript/text before processing.")
async def patch_source(
    source_id: int,
    payload: SourcePatchRequest,
    session: Session = Depends(get_session),
):
    return await journalService.update_source_text(session, source_id, payload.text)


@router.post("/source/process/{source_id}", tags=["Source"], description="Process a source by its ID. This endpoint performs chunking and vector indexing for sources that already have text/transcript.")
async def process_source(
    source_id: int,
    session: Session = Depends(get_session),
):
    return await journalService.process_source(session, source_id)