from datetime import datetime
from typing import Any, Optional
from sqlmodel import Session, select
from database.models import Chat, Chunk, Source, SourceTag
from app.services.ranking import SourceMeta

def get_all_sources(session: Session):
    return session.exec(
        select(Source).order_by(Source.created_at.desc(), Source.id.desc())
    ).all()


def get_source_ids_in_range(session: Session, start: datetime, end: datetime) -> list[int]:
    """Ids of processed (indexed, hence searchable) sources whose created_at
    falls in ``[start, end)``. Returns ints."""
    return list(
        session.exec(
            select(Source.id).where(
                Source.created_at >= start,
                Source.created_at < end,
                Source.status == "processed",
            )
        ).all()
    )


def get_sources_meta(session: Session, source_ids: list[int]) -> dict[int, SourceMeta]:
    """Fetch created_at for the given sources, keyed by int id, to recency-weight a candidate set."""
    if not source_ids:
        return {}
    rows = session.exec(
        select(Source.id, Source.created_at).where(Source.id.in_(source_ids))
    ).all()
    return {sid: SourceMeta(created_at=created_at) for sid, created_at in rows}

def get_sources_since(session: Session, since_id: int):
    return session.exec(
        select(Source)
        .where(Source.id > since_id)
        .order_by(Source.created_at.desc(), Source.id.desc())
    ).all()

def get_source_by_id(session: Session, source_id: int) -> Source:
    return session.exec(select(Source).where(Source.id == source_id)).first()


def get_latest_source(session: Session) -> Source:
    return session.exec(select(Source).order_by(Source.id.desc())).first()

def get_unprocessed_sources_query():
    return select(Source).where(Source.status == "not processed")

def filename_exists(session: Session, filename: str) -> bool:
    return session.exec(select(Source.id).where(Source.filename == filename)).first() is not None

def create_source(
    session: Session,
    *,
    status: str,
    text: Optional[str] = None,
    text_html: Optional[str] = None,
    filename: Optional[str] = None,
    file_path: Optional[str] = None,
    file_type: Optional[str] = None,
    transcript_segments: Optional[list] = None,
    created_at: Optional[datetime] = None,
) -> Source:
    now = datetime.utcnow()
    new_source = Source(
        text=text,
        text_html=text_html,
        filename=filename,
        file_path=file_path,
        file_type=file_type,
        transcript_segments=transcript_segments,
        status=status,
        created_at=created_at or now,
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

        session.commit()

        for chunk in db_chunks:
            session.refresh(chunk)

        return db_chunks
    except Exception as exc:
        session.rollback()
        print(f"Error creating chunks for source {source_id}: {exc}")
        raise exc


def update_source_summary(
    session: Session, source: Source, summary: str, provenance: Optional[dict] = None
) -> Source:
    """Persist the LLM summary and merge its provenance into derived_meta.

    Reassigns derived_meta to a new dict so SQLAlchemy detects the JSON change.
    """
    source.summary = summary
    # A freshly generated summary supersedes any prior hand-edited HTML.
    source.summary_html = None
    if provenance is not None:
        meta = dict(source.derived_meta or {})
        meta["summary"] = provenance
        source.derived_meta = meta
    source.edited_at = datetime.utcnow()
    session.add(source)
    session.commit()
    session.refresh(source)
    return source


def get_chunks_for_source(session: Session, source_id: int) -> list[Chunk]:
    return session.exec(
        select(Chunk).where(Chunk.source_id == source_id).order_by(Chunk.chunk_index)
    ).all()


def update_source_status(session: Session, source: Source, status: str) -> Source:
    source.status = status
    source.edited_at = datetime.utcnow()
    session.add(source)
    session.commit()
    session.refresh(source)
    return source


def update_source_text(session: Session, source: Source, text: str) -> Source:
    source.text = text
    source.edited_at = datetime.utcnow()

    session.add(source)
    session.commit()
    session.refresh(source)

    return source


def update_source_fields(
    session: Session,
    source: Source,
    *,
    text: Optional[str] = None,
    text_html: Optional[str] = None,
    summary: Optional[str] = None,
    summary_html: Optional[str] = None,
    filename: Optional[str] = None,
    created_at_str: Optional[str] = None,
    status: Optional[str] = None,
) -> Source:
    if text is not None:
        source.text = text
    if text_html is not None:
        source.text_html = text_html
    if summary is not None:
        source.summary = summary
    if summary_html is not None:
        source.summary_html = summary_html
    if filename is not None:
        source.filename = filename
    if created_at_str is not None:
        source.created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00")).replace(tzinfo=None)
    if status is not None:
        source.status = status
    source.edited_at = datetime.utcnow()
    session.add(source)
    session.commit()
    session.refresh(source)
    return source


def delete_source(session: Session, source_id: int) -> bool:
    source = session.exec(select(Source).where(Source.id == source_id)).first()
    if not source:
        return False
    chunks = session.exec(select(Chunk).where(Chunk.source_id == source_id)).all()
    for chunk in chunks:
        session.delete(chunk)
    source_tags = session.exec(select(SourceTag).where(SourceTag.source_id == source_id)).all()
    for st in source_tags:
        session.delete(st)
    linked_chats = session.exec(select(Chat).where(Chat.source_id == source_id)).all()
    for chat in linked_chats:
        chat.source_id = None
        session.add(chat)
    session.delete(source)
    session.commit()
    return True


def update_source_transcript(session: Session, source: Source, text: str, segments: list) -> Source:
    source.text = text
    source.transcript_segments = segments
    source.edited_at = datetime.utcnow()

    session.add(source)
    session.commit()
    session.refresh(source)

    return source