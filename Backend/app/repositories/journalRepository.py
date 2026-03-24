from datetime import datetime

from typing import Optional

from sqlmodel import Session, select

from database.models import Chunk, Journal

def get_all_journals(session: Session):
    return session.exec(select(Journal)).all()

def get_journal_by_id(session: Session, journal_id: int) -> Journal:
    return session.exec(select(Journal).where(Journal.id == journal_id)).first()


def get_latest_journal(session: Session) -> Journal:
    return session.exec(select(Journal).order_by(Journal.id.desc())).first()

def get_unprocessed_journals_query():
    return select(Journal).where(Journal.status == "not processed")

def create_journal(
    session: Session,
    *,
    status: str,
    text: Optional[str] = None,
    filename: Optional[str] = None,
    file_path: Optional[str] = None,
    file_type: Optional[str] = None,
) -> Journal:
    now = datetime.now()
    new_journal = Journal(
        text=text,
        filename=filename,
        file_path=file_path,
        file_type=file_type,
        status=status,
        created_at=now,
        edited_at=now,
    )
    session.add(new_journal)
    session.commit()
    session.refresh(new_journal)
    return new_journal


def create_chunks(session: Session, journal_id: int, chunks: list[str]) -> list[Chunk]:
    journal = session.exec(select(Journal).where(Journal.id == journal_id)).first()
    if not journal:
        raise ValueError(f"Journal {journal_id} not found")

    db_chunks: list[Chunk] = []
    for chunk_text in chunks:
        chunk = Chunk(journal_id=journal_id, chunk_text=chunk_text)
        session.add(chunk)
        db_chunks.append(chunk)

    journal.status = "processed"
    journal.edited_at = datetime.now()
    session.commit()

    for chunk in db_chunks:
        session.refresh(chunk)

    return db_chunks


def revert_processing(session: Session, journal_id: int, chunk_ids: list[int]) -> Journal:
    journal = session.exec(select(Journal).where(Journal.id == journal_id)).first()
    if not journal:
        raise ValueError(f"Journal {journal_id} not found")

    if chunk_ids:
        chunks_to_delete = session.exec(select(Chunk).where(Chunk.id.in_(chunk_ids))).all()
        for chunk in chunks_to_delete:
            session.delete(chunk)

    journal.status = "not processed"
    journal.edited_at = datetime.now()

    session.add(journal)
    session.commit()
    session.refresh(journal)

    return journal