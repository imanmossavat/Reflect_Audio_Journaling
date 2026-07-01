"""Fixtures for repository-level tests (docs/DB_TESTING_PROPOSAL.md).

Two schema sources are deliberately kept separate:

- `session` — schema built directly from the current SQLModel classes via
  `create_all()`. Fast, fully isolated, per-test. Validates repository
  *logic* (merges, filters, provenance writes).

- `migrated_session` — schema produced by actually running the real Alembic
  migration chain against a throwaway on-disk SQLite file. Slower (runs
  once per test session), but validates that migrations produce what the
  ORM models expect -- catching drift like docs/ISSUES.md #17, which is
  exactly the kind of gap a new provenance migration could reintroduce.
"""
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from database.models import *  # noqa: F401,F403 -- register all tables on SQLModel.metadata


@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture(scope="session")
def migrated_engine(tmp_path_factory):
    """Run `alembic upgrade head` once, against a throwaway on-disk file.

    migrations/env.py imports `engine` directly from `app.db` (not from
    alembic.ini's sqlalchemy.url -- see env.py's run_migrations_online),
    and app/db.py hardcodes that engine to the real
    Backend/database/database.db with no override hook. So the only safe
    way to redirect migrations to a throwaway file is to swap
    `app.db.engine` for the duration of the upgrade, then restore it --
    never touch the real dev database.
    """
    import app.db as app_db
    from alembic import command
    from alembic.config import Config

    backend_dir = Path(__file__).resolve().parents[2]
    db_path = tmp_path_factory.mktemp("migrated_db") / "test.db"
    test_engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

    original_engine = app_db.engine
    original_db_path = Path(app_db.DB_PATH).resolve()
    assert original_db_path != db_path.resolve(), "refusing to run migrations against the real database file"

    app_db.engine = test_engine
    try:
        cfg = Config(str(backend_dir / "alembic.ini"))
        command.upgrade(cfg, "head")
    finally:
        app_db.engine = original_engine

    return test_engine


@pytest.fixture
def migrated_session(migrated_engine):
    """One test's worth of isolation on top of the shared migrated engine:
    wrap each test in a transaction and roll it back afterward, so tests
    don't see each other's rows despite sharing the (expensive to build)
    migrated schema."""
    connection = migrated_engine.connect()
    transaction = connection.begin()
    s = Session(bind=connection)
    try:
        yield s
    finally:
        s.close()
        transaction.rollback()
        connection.close()
