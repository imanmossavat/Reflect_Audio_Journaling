import asyncio
import mimetypes
import os
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlmodel import Session

from app.db import get_session
from app.schemas.journalSchemas import SourcePatchRequest
from app.services import sourceService
from app.services.ollama_gate import generation_lock

router = APIRouter()

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".webm", ".ogg", ".txt", ".md"}
ALLOWED_MIME_TYPES = {"audio/mpeg", "audio/wav", "audio/webm", "audio/ogg", "text/plain", "text/markdown"}

@router.get("/sources", tags=["Source"])
async def get_all_sources(
    session: Session = Depends(get_session),
    since_id: int = 0,
):
    if since_id > 0:
        return sourceService.get_sources_since(session, since_id)
    return sourceService.get_all_sources(session)

@router.get("/unprocessed-sources", tags=["Source"])
async def get_unprocessed_sources(
    session: Session = Depends(get_session),
):
    return sourceService.get_unprocessed_sources(session)

@router.get("/source/{source_id}", tags=["Source"])
async def get_source_by_id(
    source_id: int,
    session: Session = Depends(get_session),
):
    return sourceService.get_source_by_id(session, source_id)


@router.get("/source-text/{source_id}", tags=["Source"])
async def get_source_text(
    source_id: int,
    session: Session = Depends(get_session),
):
    source = sourceService.get_source_by_id(session, source_id)
    return source.text


@router.get("/source/{source_id}/chunks", tags=["Source"], description="Semantic chunks the source was split into for retrieval.")
async def get_source_chunks(
    source_id: int,
    session: Session = Depends(get_session),
):
    return sourceService.get_source_chunks(session, source_id)


@router.post("/source/{source_id}/summary/regenerate", tags=["Source"], description="Regenerate the LLM summary for a source.")
async def regenerate_source_summary(
    source_id: int,
    session: Session = Depends(get_session),
):
    source = sourceService.get_source_by_id(session, source_id)
    if not source.text or not source.text.strip():
        raise HTTPException(status_code=422, detail="Source has no text to summarise yet.")
    # Serialize against chat generation; the summary call is synchronous, so run it
    # off the event loop.
    async with generation_lock:
        return await asyncio.to_thread(sourceService.regenerate_summary, source_id)


@router.post("/source/uploadFile/processed", tags=["Source"], description="Upload a source file. Returns immediately; transcription and indexing run in the background.")
async def upload_source(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    extension = os.path.splitext(file.filename)[1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type. Only .wav, .mp3, .txt and .md files are supported.")
    source = await sourceService.save_processed_source_file(session, file)
    background_tasks.add_task(sourceService._process_source_background, source.id)
    return source


@router.post("/source/uploadFile/raw", tags=["Source"], description="Upload a source file that stays raw and unprocessed. No transcription or chunk processing is run at upload time.")
async def upload_raw_source(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    extension = os.path.splitext(file.filename)[1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file extension type.")
    return await sourceService.save_raw_source_file(session, file)

@router.post("/source/uploadText/processed", tags=["Source"], description="Upload a source as text. Returns immediately; chunking and indexing run in the background.")
async def upload_text_source(
    background_tasks: BackgroundTasks,
    source_text: str = Form(""),
    source_html: str | None = Form(None),
    session: Session = Depends(get_session),
):
    source = await sourceService.save_processed_source_text(session, source_text, source_html)
    background_tasks.add_task(sourceService._process_source_background, source.id)
    return source


@router.post("/source/uploadText/raw", tags=["Source"], description="Upload a source as raw text. The source is stored as not processed and can be processed later.")
async def upload_raw_text_source(
    source_text: str = Form(...),
    session: Session = Depends(get_session),
):
    return await sourceService.save_raw_source_text(session, source_text)


@router.post("/source/transcribe/{source_id}", tags=["Source"], description="Transcribe an audio source by its ID. This endpoint only performs transcription and stores editable transcript text.")
async def transcribe_source(
    source_id: int,
    session: Session = Depends(get_session),
):
    return await sourceService.transcribe_source(session, source_id)


@router.patch("/source/{source_id}", tags=["Source"], description="Update source fields (text, filename, created_at).")
async def patch_source(
    source_id: int,
    payload: SourcePatchRequest,
    session: Session = Depends(get_session),
):
    return await sourceService.update_source(
        session, source_id, text=payload.text, text_html=payload.text_html,
        summary=payload.summary, summary_html=payload.summary_html,
        filename=payload.filename, created_at_str=payload.created_at
    )


@router.delete("/source/{source_id}", tags=["Source"], description="Delete a source and its associated data.")
async def delete_source(
    source_id: int,
    session: Session = Depends(get_session),
):
    return await sourceService.delete_source(session, source_id)


@router.post("/source/process/{source_id}", tags=["Source"], description="Queue a raw source for processing. Returns immediately; processing runs in the background.")
async def process_source(
    source_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    source = await sourceService.process_source(session, source_id)
    background_tasks.add_task(sourceService._process_source_background, source_id)
    return source


INBOX = Path(__file__).parent.parent.parent / "database" / "inbox"


@router.post("/source/drop-to-inbox", tags=["Source"], description="Drop a file into the inbox folder for automatic processing by the file watcher.")
async def drop_file_to_inbox(
    file: UploadFile = File(...),
):
    extension = os.path.splitext(file.filename or "")[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type.")
    INBOX.mkdir(parents=True, exist_ok=True)
    dest = INBOX / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"queued": True, "filename": dest.name}


@router.post("/source/drop-text-to-inbox", tags=["Source"], description="Write a text note into the inbox folder for automatic processing by the file watcher.")
async def drop_text_to_inbox(
    source_text: str = Form(...),
):
    INBOX.mkdir(parents=True, exist_ok=True)
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_note.txt"
    dest = INBOX / filename
    dest.write_text(source_text, encoding="utf-8")
    return {"queued": True, "filename": filename}


@router.get("/source/{source_id}/audio", tags=["Source"], description="Stream the audio file for an audio source.")
async def get_source_audio(
    source_id: int,
    session: Session = Depends(get_session),
):
    source = sourceService.get_source_by_id(session, source_id)
    if source.file_type != "audio":
        raise HTTPException(status_code=400, detail="Source is not an audio file.")
    if not source.file_path or not os.path.isfile(source.file_path):
        raise HTTPException(status_code=404, detail="Audio file not found on disk.")
    media_type, _ = mimetypes.guess_type(source.file_path)
    return FileResponse(source.file_path, media_type=media_type or "audio/mpeg")
