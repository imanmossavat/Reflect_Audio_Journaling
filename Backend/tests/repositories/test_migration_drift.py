"""Round-trip tests against a real, fully-migrated SQLite schema (not the
ORM-model-derived schema the `session` fixture uses elsewhere).

See docs/DB_TESTING_PROPOSAL.md's resolved "open question": in-memory
SQLite via `create_all()` validates repository logic but bypasses
migrations entirely, so it can't catch drift between what a migration
actually created and what the SQLModel class now expects. docs/ISSUES.md
#17 confirmed that drift already exists (`alembic check` fails on 4
columns: chat_message.thinking, source.text_html, source.summary,
source.summary_html -- hand-written migrations used sa.Text(), the models
declare bare `str`, which SQLModel maps to AutoString()).

That drift happens to be harmless on SQLite (TEXT and VARCHAR-without-length
are storage-identical there), which is exactly why a functional round-trip
test is the right check here rather than a strict type-equality assertion:
it proves the drifted columns still work today, and it will catch it if a
*future* migration (e.g. the provenance retrofit's) drifts in a way that
actually breaks storage or retrieval.
"""
from database.models import ChatMessage, Chat, Source


def test_drifted_text_columns_round_trip_through_real_migrated_schema(migrated_session):
    long_text = "x" * 5000  # long enough that a silent VARCHAR truncation would show up

    source = Source(summary=long_text, summary_html=f"<p>{long_text}</p>", text_html=f"<p>{long_text}</p>")
    migrated_session.add(source)
    migrated_session.commit()
    migrated_session.refresh(source)

    assert source.summary == long_text
    assert source.summary_html == f"<p>{long_text}</p>"
    assert source.text_html == f"<p>{long_text}</p>"

    chat = Chat()
    migrated_session.add(chat)
    migrated_session.commit()
    migrated_session.refresh(chat)

    message = ChatMessage(chat_id=chat.id, role="assistant", text="answer", thinking=long_text)
    migrated_session.add(message)
    migrated_session.commit()
    migrated_session.refresh(message)

    assert message.thinking == long_text


def test_migrated_schema_has_source_tag_origin_column(migrated_session):
    """Sanity check that the migrated engine actually ran the migration
    chain (not just created an empty file) -- origin was added by a
    specific migration (f8c6d7e9a0b2), not by the initial schema."""
    from sqlalchemy import inspect

    inspector = inspect(migrated_session.get_bind())
    columns = {col["name"] for col in inspector.get_columns("source_tag")}
    assert "origin" in columns
