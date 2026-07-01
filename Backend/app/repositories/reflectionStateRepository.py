from datetime import datetime
from typing import Optional

from sqlmodel import Session

from database.models import ReflectionState as ReflectionStateRow


def get_by_chat_id(session: Session, chat_id: int) -> Optional[ReflectionStateRow]:
    return session.get(ReflectionStateRow, chat_id)


def upsert(
    session: Session,
    chat_id: int,
    *,
    sources: list,
    focus: dict,
    gist: dict,
    open_thread: dict,
) -> ReflectionStateRow:
    """One row per chat_id (Document B §2) — created on first use, updated in
    place on every subsequent turn. Not versioned."""
    row = session.get(ReflectionStateRow, chat_id)
    now = datetime.utcnow()
    if row is None:
        row = ReflectionStateRow(
            chat_id=chat_id, sources=sources, focus=focus, gist=gist, open_thread=open_thread,
            updated_at=now,
        )
        session.add(row)
    else:
        row.sources = sources
        row.focus = focus
        row.gist = gist
        row.open_thread = open_thread
        row.updated_at = now
    session.commit()
    session.refresh(row)
    return row
