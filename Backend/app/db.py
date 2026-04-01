from pathlib import Path

from fastapi import HTTPException
from sqlmodel import Session, create_engine, select

from database.models import Journal


# Database
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR.parent / "database" / "database.db"
sqlite_url = f"sqlite:///{DB_PATH.as_posix()}"

engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})


def get_session():
    with Session(engine) as session:
        yield session


def get_latest_journal(session: Session) -> Journal:
    journal = session.exec(select(Journal).order_by(Journal.id.desc())).first()
    if not journal:
        raise HTTPException(status_code=404, detail="No journal uploaded yet.")
    if not journal.text:
        raise HTTPException(status_code=404, detail="Journal is empty.")
    return journal
