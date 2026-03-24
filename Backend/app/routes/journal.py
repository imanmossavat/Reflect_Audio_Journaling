from fastapi import APIRouter, Depends, HTTPException,  UploadFile, File, Form 
from sqlmodel import Session

from app.db import get_session
from app.services import journalService

import os

router = APIRouter()

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a",".txt", ".md"}
ALLOWED_MIME_TYPES = {"audio/mpeg", "audio/wav", "text/plain", "text/markdown"}

@router.get("/journals", tags=["Journal"])
async def get_all_journals(
    session: Session = Depends(get_session),
):
    return journalService.get_all_journals(session)

@router.get("/unprocessed-journals", tags=["Journal"])
async def get_unprocessed_journals(
    session: Session = Depends(get_session),
):
    return journalService.get_unprocessed_journals(session)

@router.get("/journal/{journal_id}", tags=["Journal"])
async def get_journal_by_id(
    journal_id: int,
    session: Session = Depends(get_session),
):
    return journalService.get_journal_by_id(session, journal_id)


@router.get("/journal-text/{journal_id}", tags=["Journal"])
async def get_journal_text(
    journal_id: int,
    session: Session = Depends(get_session),
):
    journal = journalService.get_journal_by_id(session, journal_id)
    return journal.text


@router.post("/journal/uploadFile/processed", tags=["Journal"], description="Upload a journal file that will be processed immediately. Transcription is performed if the file is an audio file. Only supports: .wav, .mp3, .txt and .md files.")
async def upload_journal(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    extension = os.path.splitext(file.filename)[1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type. Only .wav, .mp3, .txt and .md files are supported.")
    return await journalService.save_processed_journal_file(session, file)


@router.post("/journal/uploadFile/raw", tags=["Journal"], description="Upload a journal file that will be processed later. Transcription is performed if the file is an audio file. Only supports: .wav, .mp3, .txt and .md files.")
async def upload_raw_journal(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    extension = os.path.splitext(file.filename)[1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file extension type.")
    return await journalService.save_raw_journal_file(session, file)

@router.post("/journal/uploadText/processed", tags=["Journal"], description="Upload a journal as text. The journal will be processed immediately.")
async def upload_text_journal(
    journal_text: str = Form(...),
    session: Session = Depends(get_session),
):
    return await journalService.save_processed_journal_text(session, journal_text)


@router.post("/journal/uploadText/raw", tags=["Journal"], description="Upload a journal as raw text. The journal will be processed immediately.")
async def upload_text_journal(
    journal_text: str = Form(...),
    session: Session = Depends(get_session),
):
    return await journalService.save_raw_journal_text(session, journal_text)


@router.post("/journal/process/{journal_id}", tags=["Journal"], description="Process a journal by its ID. This is for journals that were uploaded as raw and need to be processed later. Processing includes transcription, chunking and indexing.")
async def process_journal(
    journal_id: int,
    session: Session = Depends(get_session),
):
    return await journalService.process_journal(session, journal_id)