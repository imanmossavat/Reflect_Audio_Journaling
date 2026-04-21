import os
import uuid

from pathlib import Path
from app.schemas.journalSchemas import SimpleRecording
from fastapi import HTTPException, UploadFile
from sqlmodel import Session
import strip_markdown

from app.repositories import sourceRepository
from app.services.chunking import chunk_text
from app.services.rag import index_chunks
from app.services.transcription import TranscriptionManager
from app import     logging_config


BASE_DIR = Path(__file__).resolve().parent.parent.parent / "database" / "uploads"
(BASE_DIR / "audio").mkdir(parents=True, exist_ok=True)
(BASE_DIR / "text").mkdir(parents=True, exist_ok=True)
logger = logging_config.logger

def get_all_sources(session: Session):
    return sourceRepository.get_all_sources(session)

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

    if file_type == "audio":
        try:
            recording = SimpleRecording(path=str(filepath), id=str(uuid.uuid4()))
            text = TranscriptionManager().transcribe(recording).text
        except NotImplementedError as exc:
            raise HTTPException(status_code=501, detail=str(exc)) from exc
    else:
        text = raw_bytes.decode("utf-8")
    
    source = sourceRepository.create_source(
        session=session,
        filename=file.filename,
        file_path=str(filepath),
        file_type=file_type,
        text=text,
        status="processed",
    )

    chunks = chunk_text(strip_markdown.strip_markdown(text) if file_type == "markdown" else text, source.id)
    if not chunks:
        session.rollback()
        raise HTTPException(status_code=500, detail="Chunk generation produced no chunks.")

    try:
        db_chunks = sourceRepository.create_chunks(session, source.id, chunks)
    except Exception as exc:
        logger.exception(f"Failed to persist chunks for source {source.id}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to save source chunks.") from exc

    try:
        index_chunks([
            {"id": str(chunk.id), "text": chunk.chunk_text, "source_id": str(source.id)}
            for chunk in db_chunks
        ])
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail="Failed to index source chunks.") from exc

    return source



async def save_processed_source_text(session: Session, source_text: str):
    source = sourceRepository.create_source(session=session, text=source_text, status="processed")
    chunks = chunk_text(source_text, source.id)
    if not chunks:
        session.rollback()
        raise HTTPException(status_code=500, detail="Chunk generation produced no chunks.")

    try:
        db_chunks = sourceRepository.create_chunks(session, source.id, chunks)
        logger.info(f"Created {len(db_chunks)} chunks, first chunk attrs: {vars(db_chunks[0])}")
    except Exception as exc:
        logger.exception(f"Failed to persist chunks for source {source.id}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to save source chunks.") from exc

    try:
        index_chunks(
            [
                {"id": str(chunk.id), "text": chunk.chunk_text, "source_id": str(source.id)}
                for chunk in db_chunks
            ]
        )
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail="Failed to index source chunks.") from exc

    return source

async def save_raw_source_text(session: Session, source_text: str):
    source = sourceRepository.create_source(session=session, text=source_text, status="not processed")
    return source


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
        transcript_text = TranscriptionManager().transcribe(recording).text
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc

    return sourceRepository.update_source_text(session, source, transcript_text)


async def update_source_text(session: Session, source_id: int, source_text: str):
    source = sourceRepository.get_source_by_id(session, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found.")

    if source.status == "processed":
        raise HTTPException(status_code=400, detail="Cannot edit a processed source.")

    return sourceRepository.update_source_text(session, source, source_text)


async def process_source(session: Session, source_id: int):
    source = sourceRepository.get_source_by_id(session, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found.")
    if source.status == "processed":
        raise HTTPException(status_code=400, detail="Source is already processed.")

    if source.text is None:
        if source.file_type in ("text", "markdown"):
            if not source.file_path:
                raise HTTPException(status_code=400, detail="No file path found for text source.")
            with open(source.file_path, "r", encoding="utf-8") as f:
                source.text = f.read()
            source = sourceRepository.update_source_text(session, source, source.text)
        elif source.file_type == "audio":
            if not source.file_path:
                raise HTTPException(status_code=400, detail="No file path found for audio source.")
            try:
                recording = SimpleRecording(path=source.file_path, id=str(source.id))
                transcript_text = TranscriptionManager().transcribe(recording).text
            except NotImplementedError as exc:
                raise HTTPException(status_code=501, detail=str(exc)) from exc

            if not transcript_text or not transcript_text.strip():
                raise HTTPException(status_code=500, detail="Transcription produced no text.")

            source = sourceRepository.update_source_text(session, source, transcript_text)
        else:
            raise HTTPException(status_code=400, detail="Cannot process source without text or file.")

    if source.file_type == "markdown":
        text_to_chunk = strip_markdown.strip_markdown(source.text)
    else:
        text_to_chunk = source.text

    chunks = chunk_text(text_to_chunk, source.id)
    if not chunks:
        session.rollback()
        raise HTTPException(status_code=500, detail="Chunk generation produced no chunks.")

    try:
        db_chunks = sourceRepository.create_chunks(session, source.id, chunks)
    except Exception as exc:
        logger.exception(f"Failed to persist chunks for source {source.id}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to save source chunks.") from exc

    chunk_dicts = [
        {
            "id": str(chunk.id),
            "text": chunk.chunk_text,
            "source_id": str(source.id),
        }
        for chunk in db_chunks
    ]

    try:
        index_chunks(chunk_dicts)
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail="Failed to index source chunks.") from exc

    return source