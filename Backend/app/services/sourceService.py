import asyncio
import os
import uuid

from pathlib import Path
from app.schemas.journalSchemas import SimpleRecording
from fastapi import HTTPException, UploadFile
from sqlmodel import Session
import strip_markdown

from app.db import engine
from app.repositories import sourceRepository
from app.services.chunking import chunk_text
from app.services.rag import index_chunks
from app.services.transcription import TranscriptionManager
from app import logging_config


BASE_DIR = Path(__file__).resolve().parent.parent.parent / "database" / "uploads"
(BASE_DIR / "audio").mkdir(parents=True, exist_ok=True)
(BASE_DIR / "text").mkdir(parents=True, exist_ok=True)
logger = logging_config.logger

#Background processing

def _set_status(source_id: int, status: str) -> None:
    """Tiny short-lived write so SQLite is never locked during long operations."""
    with Session(engine) as session:
        source = sourceRepository.get_source_by_id(session, source_id)
        if source:
            sourceRepository.update_source_status(session, source, status)


def _process_source_sync(source_id: int) -> None:
    """Full processing pipeline — safe to run in a thread pool.
    Each DB interaction uses its own short-lived session so SQLite is only
    locked for milliseconds, never for the duration of transcription / LLM calls.
    """
    #Read initial source state
    with Session(engine) as session:
        source = sourceRepository.get_source_by_id(session, source_id)
        if not source:
            logger.error(f"Background task: source {source_id} not found")
            return
        file_type = source.file_type
        file_path = source.file_path
        text = source.text

    try:
        #Transcribe
        if file_type == "audio" and not text:
            _set_status(source_id, "transcribing")
            if not file_path:
                logger.error(f"No file path for audio source {source_id}")
                _set_status(source_id, "failed")
                return
            recording = SimpleRecording(path=file_path, id=str(source_id))
            try:
                transcript = TranscriptionManager().transcribe(recording)
            except NotImplementedError as exc:
                logger.error(f"Transcription unavailable for source {source_id}: {exc}")
                _set_status(source_id, "failed")
                return
            text = transcript.text
            segments = [
                {"text": s.text, "start_s": s.start_s, "end_s": s.end_s}
                for s in transcript.sentences
            ]
            if not text or not text.strip():
                logger.error(f"Transcription produced no text for source {source_id}")
                _set_status(source_id, "failed")
                return
            # Short-lived write to save transcript
            with Session(engine) as session:
                source_obj = sourceRepository.get_source_by_id(session, source_id)
                if not source_obj:
                    return
                sourceRepository.update_source_transcript(session, source_obj, text, segments)

        if not text or not text.strip():
            logger.error(f"No text to process for source {source_id}")
            _set_status(source_id, "failed")
            return

        #Chunk
        _set_status(source_id, "chunking")
        text_to_chunk = strip_markdown.strip_markdown(text) if file_type == "markdown" else text
        chunks = chunk_text(text_to_chunk, source_id)
        if not chunks:
            logger.error(f"No chunks generated for source {source_id}")
            _set_status(source_id, "failed")
            return

        # Short-lived write to persist chunks
        with Session(engine) as session:
            db_chunks = sourceRepository.create_chunks(session, source_id, chunks)
            chunk_dicts = [
                {"id": str(c.id), "text": c.chunk_text, "source_id": str(source_id)}
                for c in db_chunks
            ]

        #Vector index (ChromaDB)
        _set_status(source_id, "indexing")
        index_chunks(chunk_dicts)

        _set_status(source_id, "processed")
        logger.info(f"Background processing complete for source {source_id}")

    except Exception as exc:
        logger.exception(f"Background processing failed for source {source_id}: {exc}")
        _set_status(source_id, "failed")


async def _process_source_background(source_id: int) -> None:
    await asyncio.to_thread(_process_source_sync, source_id)


#Functions

def get_all_sources(session: Session):
    return sourceRepository.get_all_sources(session)

def get_sources_since(session: Session, since_id: int):
    return sourceRepository.get_sources_since(session, since_id)

def get_source_by_id(session: Session, source_id: int) -> dict:
	source = sourceRepository.get_source_by_id(session, source_id)
	if not source:
		raise HTTPException(status_code=404, detail="Source not found.")

	return source

def get_unprocessed_sources(session: Session):
    return session.exec(
        sourceRepository.get_unprocessed_sources_query()
    ).all()

async def save_raw_source_file(session: Session, file: UploadFile):
    ext = os.path.splitext(file.filename)[1].lower()
    content_type = file.content_type or ""

    if content_type.startswith("audio/") or ext in [".wav", ".mp3", ".m4a"]:
        file_type = "audio"
        subfolder = "audio"
    elif ext == ".md":
        file_type = "markdown"
        subfolder = "text"
    elif ext == ".txt":
        file_type = "text"
        subfolder = "text"
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    file_id = uuid.uuid4()
    disk_filename = f"{file_id}{ext}"
    filepath = BASE_DIR / subfolder / disk_filename

    raw_bytes = await file.read()
    with open(filepath, "wb") as f:
        f.write(raw_bytes)

    source = sourceRepository.create_source(
        session=session,
        filename=file.filename,
        file_path=str(filepath),
        file_type=file_type,
        status="not processed",
    )

    return source


async def save_processed_source_file(session: Session, file: UploadFile):
    """Save the file and create the source record. Processing runs as a background task."""
    ext = os.path.splitext(file.filename)[1].lower()
    content_type = file.content_type or ""

    if content_type.startswith("audio/") or ext in [".wav", ".mp3", ".m4a"]:
        file_type = "audio"
        subfolder = "audio"
    elif ext == ".md":
        file_type = "markdown"
        subfolder = "text"
    elif ext == ".txt":
        file_type = "text"
        subfolder = "text"
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    file_id = uuid.uuid4()
    disk_filename = f"{file_id}{ext}"
    filepath = BASE_DIR / subfolder / disk_filename

    raw_bytes = await file.read()
    with open(filepath, "wb") as f:
        f.write(raw_bytes)

    # Store text immediately for non-audio files so the background task can skip reading from disk
    text = raw_bytes.decode("utf-8") if file_type in ("text", "markdown") else None

    return sourceRepository.create_source(
        session=session,
        filename=file.filename,
        file_path=str(filepath),
        file_type=file_type,
        text=text,
        status="queued",
    )


async def save_processed_source_text(session: Session, source_text: str):
    """Save raw text and return immediately. Processing runs as a background task."""
    return sourceRepository.create_source(session=session, text=source_text, status="queued")

async def save_raw_source_text(session: Session, source_text: str):
    return sourceRepository.create_source(session=session, text=source_text, status="not processed")


async def transcribe_source(session: Session, source_id: int):
    source = sourceRepository.get_source_by_id(session, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found.")

    if source.file_type != "audio":
        raise HTTPException(status_code=400, detail="Only audio sources can be transcribed.")

    if not source.file_path:
        raise HTTPException(status_code=400, detail="No file path found for audio source.")

    try:
        recording = SimpleRecording(path=source.file_path, id=str(source.id))
        transcript = TranscriptionManager().transcribe(recording)
        transcript_text = transcript.text
        segments = [
            {"text": s.text, "start_s": s.start_s, "end_s": s.end_s}
            for s in transcript.sentences
        ]
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc

    return sourceRepository.update_source_transcript(session, source, transcript_text, segments)


async def update_source_text(session: Session, source_id: int, source_text: str):
    source = sourceRepository.get_source_by_id(session, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found.")

    if source.status == "processed":
        raise HTTPException(status_code=400, detail="Cannot edit a processed source.")

    return sourceRepository.update_source_text(session, source, source_text)


async def process_source(session: Session, source_id: int):
    """Queue a raw/unprocessed source for background processing."""
    source = sourceRepository.get_source_by_id(session, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found.")
    if source.status == "processed":
        raise HTTPException(status_code=400, detail="Source is already processed.")

    return sourceRepository.update_source_status(session, source, "queued")
