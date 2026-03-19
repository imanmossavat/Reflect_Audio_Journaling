from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException
from sqlmodel import Session

from app.db import engine, get_latest_journal
from app.services.chunking import chunk_text
from app.services.rag import index_chunks
from database.models import Journal, Chunk

router = APIRouter()


@router.post("/upload", tags=["Journal"])
async def upload_journal(file: UploadFile = File(...)):
    if file.content_type != "text/plain":
        raise HTTPException(status_code=400, detail="Only plain text files are allowed.")

    content = await file.read()
    text = content.decode("utf-8")
    word_count = len(text.split())
    now = datetime.utcnow()

    with Session(engine) as session:
        # 1. Store journal in SQLite
        journal_entry = Journal(
            text=text,
            source_type=file.content_type,
            created_at=now,
            edited_at=now,
        )
        session.add(journal_entry)
        session.commit()
        session.refresh(journal_entry)
        journal_id = journal_entry.id

        # 2. Split into chunks
        raw_chunks = chunk_text(text)

        # 3. Store chunks in SQLite
        db_chunks = []
        for chunk_text_content in raw_chunks:
            chunk = Chunk(
                journal_id=journal_id,
                chunk_text=chunk_text_content,
            )
            session.add(chunk)
            session.commit()
            session.refresh(chunk)
            db_chunks.append({"id": chunk.id, "text": chunk.chunk_text, "journal_id": journal_id})

    # 4+5. Embed chunks and store in ChromaDB (outside session — no DB needed)
    index_chunks(db_chunks)

    return {
        "word_count": word_count,
        "filename": file.filename,
        "journal_id": journal_id,
        "chunks_created": len(db_chunks),
    }


@router.get("/journal-text", tags=["Journal"])
async def get_journal_text():
    with Session(engine) as session:
        journal = get_latest_journal(session)
        return {"journal_text": journal.text}