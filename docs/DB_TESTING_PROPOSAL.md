# Proposal: repository-level DB tests

## Problem

Every existing test mocks `sourceRepository` (or `sourceService`) rather than
hitting a real database, so repository logic itself is never verified. Two
functions in particular have non-trivial merge behavior that's currently
untested:

- `update_source_summary` — merges `{"summary": ...}` into `Source.derived_meta`
  without clobbering other keys.
- `update_source_transcript` — same pattern, merges `{"transcript": ...}`
  (added July 2026 alongside transcription metadata).

A bug in that merge (e.g. `source.derived_meta = provenance` instead of
`meta["transcript"] = provenance; source.derived_meta = meta`) would silently
wipe out the other artifact's provenance and no test would catch it.

## Proposal

Add a `tests/repositories/` directory with a fixture that creates a fresh
in-memory SQLite database per test, using the real `SQLModel` metadata:

```python
# tests/repositories/conftest.py
import pytest
from sqlmodel import Session, SQLModel, create_engine

from database.models import *  # noqa: F401,F403 -- register all tables


@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
```

Each test creates the rows it needs directly (e.g. `Source(...)`, `session.add`,
`session.commit`), calls the real repository function, and asserts against the
real row afterward — no mocking of the repository layer itself.

Example for the merge bug above:

```python
def test_update_source_transcript_preserves_existing_summary_meta(session):
    source = Source(derived_meta={"summary": {"model": "gemma4"}})
    session.add(source)
    session.commit()

    sourceRepository.update_source_transcript(
        session, source, "text", [], provenance={"model": "medium"}
    )

    assert source.derived_meta["summary"] == {"model": "gemma4"}
    assert source.derived_meta["transcript"] == {"model": "medium"}
```

## Scope

Don't backfill every repository function at once. Start with the two
`derived_meta`-merging functions above, since they're the ones with actual
merge logic to get wrong. Add more repository tests opportunistically when
touching that code, the same way service-level tests already exist for
`sourceService`.

## Open question

Fresh in-memory SQLite per test (shown above) is simplest and fully isolated,
but doesn't catch anything specific to the project's real SQLite file or
Alembic migration state. If that gap matters later, revisit using a
migrated on-disk SQLite temp file instead — not needed for the merge-logic
bugs this proposal targets.
