from datetime import datetime
from typing import Any, Optional
from sqlmodel import Session, select
from database.models import Chunk, Source

def get_all_sources(session: Session):
    return session.exec(select(Source)).all()

def get_source_by_id(session: Session, source_id: int) -> Source:
    return session.exec(select(Source).where(Source.id == source_id)).first()


def get_latest_source(session: Session) -> Source:
    return session.exec(select(Source).order_by(Source.id.desc())).first()

def get_unprocessed_sources_query():
    return select(Source).where(Source.status == "not processed")

def create_source(
    session: Session,
    *,
    status: str,
    text: Optional[str] = None,
    filename: Optional[str] = None,
    file_path: Optional[str] = None,
    file_type: Optional[str] = None,
) -> Source:
    now = datetime.now()
    new_source = Source(
        text=text,
        filename=filename,
        file_path=file_path,
        file_type=file_type,
        status=status,
        created_at=now,
        edited_at=now,
    )
    session.add(new_source)
    session.commit()
    session.refresh(new_source)
    return new_source


def create_chunks(session: Session, source_id: int, chunks: list[dict[str, Any]]) -> list[Chunk]:
    try:
        source = session.exec(select(Source).where(Source.id == source_id)).first()
        if not source:
            raise ValueError(f"Source {source_id} not found")

        db_chunks: list[Chunk] = []
        for idx, chunk_data in enumerate(chunks):
            chunk_text = str(chunk_data.get("text", "")).strip()
            if not chunk_text:
                continue

            # Keep caller-provided order when available, otherwise use list order.
            raw_chunk_index = chunk_data.get("chunk_index", idx)
            try:
                chunk_index = int(raw_chunk_index)
            except (TypeError, ValueError):
                chunk_index = idx

            chunk = Chunk(
                source_id=source_id,
                chunk_text=chunk_text,
                chunk_index=chunk_index,
            )
            session.add(chunk)
            db_chunks.append(chunk)

        if not db_chunks:
            raise ValueError(f"No chunks generated for source {source_id}.")

        source.status = "processed"
        source.edited_at = datetime.now()
        session.commit()

        for chunk in db_chunks:
            session.refresh(chunk)

        return db_chunks
    except Exception as exc:
        session.rollback()
        print(f"Error creating chunks for source {source_id}: {exc}")
        raise exc


def update_source_text(session: Session, source: Source, text: str) -> Source:
    source.text = text
    source.edited_at = datetime.now()

    session.add(source)
    session.commit()
    session.refresh(source)

    return source