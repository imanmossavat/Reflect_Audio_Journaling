import os
import uuid

from pathlib import Path
from app.schemas.journalSchemas import SimpleRecording
from fastapi import HTTPException, UploadFile
from sqlmodel import Session
import strip_markdown

from app.repositories import journalRepository
from app.services.chunking import chunk_text
from app.services.rag import index_chunks
from app.services.transcription import TranscriptionManager
from app import     logging_config


BASE_DIR = Path(__file__).resolve().parent.parent.parent / "database" / "uploads"
(BASE_DIR / "audio").mkdir(parents=True, exist_ok=True)
(BASE_DIR / "text").mkdir(parents=True, exist_ok=True)
logger = logging_config.logger

def get_all_journals(session: Session):
    return journalRepository.get_all_journals(session)

def get_journal_by_id(session: Session, journal_id: int) -> dict:
	journal = journalRepository.get_journal_by_id(session, journal_id)
	if not journal:
		raise HTTPException(status_code=404, detail="Journal not found.")

	return journal

def get_unprocessed_journals(session: Session):
    return session.exec(
        journalRepository.get_unprocessed_journals_query()
    ).all()

async def save_raw_journal_file(session: Session, file: UploadFile):
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

    journal = journalRepository.create_journal(
        session=session,
        filename=file.filename,
        file_path=str(filepath),
        file_type=file_type,
        status="not processed",
    )

    return journal


async def save_processed_journal_file(session: Session, file: UploadFile):
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
    
    journal = journalRepository.create_journal(
        session=session,
        filename=file.filename,
        file_path=str(filepath),
        file_type=file_type,
        text=text,
        status="processed",
    )

    chunks = chunk_text(strip_markdown.strip_markdown(text) if file_type == "markdown" else text, journal.id)
    if not chunks:
        session.rollback()
        raise HTTPException(status_code=500, detail="Chunk generation produced no chunks.")

    try:
        db_chunks = journalRepository.create_chunks(session, journal.id, chunks)
    except Exception as exc:
        logger.exception(f"Failed to persist chunks for journal {journal.id}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to save journal chunks.") from exc

    try:
        index_chunks([
            {"id": str(chunk.id), "text": chunk.chunk_text, "journal_id": str(journal.id)}
            for chunk in db_chunks
        ])
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail="Failed to index journal chunks.") from exc

    return journal



async def save_processed_journal_text(session: Session, journal_text: str):
    journal = journalRepository.create_journal(session=session, text=journal_text, status="processed")
    chunks = chunk_text(journal_text, journal.id)
    if not chunks:
        session.rollback()
        raise HTTPException(status_code=500, detail="Chunk generation produced no chunks.")

    try:
        db_chunks = journalRepository.create_chunks(session, journal.id, chunks)
        logger.info(f"Created {len(db_chunks)} chunks, first chunk attrs: {vars(db_chunks[0])}")
    except Exception as exc:
        logger.exception(f"Failed to persist chunks for journal {journal.id}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to save journal chunks.") from exc

    try:
        index_chunks(
            [
                {"id": str(chunk.id), "text": chunk.chunk_text, "journal_id": str(journal.id)}
                for chunk in db_chunks
            ]
        )
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail="Failed to index journal chunks.") from exc

    return journal

async def save_raw_journal_text(session: Session, journal_text: str):
    journal = journalRepository.create_journal(session=session, text=journal_text, status="not processed")
    return journal


async def transcribe_journal(session: Session, journal_id: int):
    journal = journalRepository.get_journal_by_id(session, journal_id)
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found.")

    if journal.file_type != "audio":
        raise HTTPException(status_code=400, detail="Only audio journals can be transcribed.")

    if not journal.file_path:
        raise HTTPException(status_code=400, detail="No file path found for audio journal.")

    try:
        recording = SimpleRecording(path=journal.file_path, id=str(journal.id))
        transcript_text = TranscriptionManager().transcribe(recording).text
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc

    return journalRepository.update_journal_text(session, journal, transcript_text)


async def update_journal_text(session: Session, journal_id: int, journal_text: str):
    journal = journalRepository.get_journal_by_id(session, journal_id)
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found.")

    if journal.status == "processed":
        raise HTTPException(status_code=400, detail="Cannot edit a processed journal.")

    return journalRepository.update_journal_text(session, journal, journal_text)


async def process_journal(session: Session, journal_id: int):
    journal = journalRepository.get_journal_by_id(session, journal_id)
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found.")
    if journal.status == "processed":
        raise HTTPException(status_code=400, detail="Journal is already processed.")

    if journal.text is None:
        if journal.file_type in ("text", "markdown"):
            if not journal.file_path:
                raise HTTPException(status_code=400, detail="No file path found for text journal.")
            with open(journal.file_path, "r", encoding="utf-8") as f:
                journal.text = f.read()
            journal = journalRepository.update_journal_text(session, journal, journal.text)
        elif journal.file_type == "audio":
            raise HTTPException(
                status_code=400,
                detail="Audio journal has no transcript yet. Run transcription first, then process.",
            )
        else:
            raise HTTPException(status_code=400, detail="Cannot process journal without text or file.")

    if journal.file_type == "markdown":
        text_to_chunk = strip_markdown.strip_markdown(journal.text)
    else:
        text_to_chunk = journal.text

    chunks = chunk_text(text_to_chunk, journal.id)
    if not chunks:
        session.rollback()
        raise HTTPException(status_code=500, detail="Chunk generation produced no chunks.")

    try:
        db_chunks = journalRepository.create_chunks(session, journal.id, chunks)
    except Exception as exc:
        logger.exception(f"Failed to persist chunks for journal {journal.id}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to save journal chunks.") from exc

    chunk_dicts = [
        {
            "id": str(chunk.id),
            "text": chunk.chunk_text,
            "journal_id": str(journal.id),
        }
        for chunk in db_chunks
    ]

    try:
        index_chunks(chunk_dicts)
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail="Failed to index journal chunks.") from exc

    return journal