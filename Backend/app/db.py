from pathlib import Path

from fastapi import HTTPException
from sqlmodel import Session, create_engine, select

from database.models import Source


# Database
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR.parent / "database" / "database.db"
sqlite_url = f"sqlite:///{DB_PATH.as_posix()}"

engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})


def get_session():
    with Session(engine) as session:
        yield session


def get_latest_source(session: Session) -> Source:
    source = session.exec(select(Source).order_by(Source.id.desc())).first()
    if not source:
        raise HTTPException(status_code=404, detail="No source uploaded yet.")
    if not source.text:
        raise HTTPException(status_code=404, detail="Source is empty.")
    return source
