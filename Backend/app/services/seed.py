"""One-time seeding of an example note for brand-new installs.

On the very first start with an empty database we insert a single example
journal entry and run it through the normal processing pipeline. That gives a
new user something to look at, a real source for the product tour to point at,
and — usefully — a built-in setup check: if Ollama or the embedding model isn't
ready, this note surfaces the failure state with a Retry button instead of
leaving the library mysteriously empty.

A sentinel file marks the seed as done, so deleting every source later never
re-inserts it.
"""

from pathlib import Path

from sqlmodel import Session, select

from app.db import engine
from app.repositories import sourceRepository
from app.utils.html_text import html_to_text
from app import logging_config
from database.models import Source

logger = logging_config.logger

_SEED_SENTINEL = Path(__file__).resolve().parents[2] / "data" / ".welcome_seeded"

WELCOME_TITLE = "Welcome to Reflect"
# Rich HTML rendered by the TipTap editor on the source page. The plain `text`
# used for chunking / embeddings / chat is derived from this via html_to_text(),
# so the two never drift.
WELCOME_HTML = (
    "<h2>Welcome to Reflect 👋</h2>"
    "<p>This is an <strong>example entry</strong> so you can see how journaling "
    "here feels. Feel free to delete it whenever you like.</p>"
    "<p>Today felt like a lot. Work was busy and I barely paused, but I did finish "
    "the report I'd been dreading, and that lifted a real weight off my shoulders. "
    "I noticed I'm calmer on the days I plan the evening before, and more scattered "
    "when I just react to whatever lands in my inbox first.</p>"
    "<p>Next week I want to carry the calmer version forward:</p>"
    "<ul>"
    "<li>Each morning, pick the <strong>three things</strong> that actually matter.</li>"
    "<li>Let the rest wait.</li>"
    "<li>Plan tomorrow the evening before.</li>"
    "</ul>"
    "<p>A few things to try right now:</p>"
    "<ul>"
    "<li>Ask Reflect a question about this entry.</li>"
    "<li>Start a <em>guided reflection</em>.</li>"
    "<li>Hit <strong>New</strong> to add your own first recording or note.</li>"
    "</ul>"
)
WELCOME_TEXT = html_to_text(WELCOME_HTML)


def _mark_seeded() -> None:
    try:
        _SEED_SENTINEL.parent.mkdir(parents=True, exist_ok=True)
        _SEED_SENTINEL.write_text("1", encoding="utf-8")
    except Exception as exc:  # noqa: BLE001 - sentinel write must never crash startup
        logger.warning(f"Could not write welcome-seed sentinel: {exc}")


def seed_welcome_note_if_needed() -> int | None:
    """Insert the example note on a fresh DB. Returns its source id so the caller
    can queue processing, or None if nothing was seeded."""
    if _SEED_SENTINEL.exists():
        return None
    try:
        with Session(engine) as session:
            existing = session.exec(select(Source.id)).first()
            if existing is not None:
                # Established journal (e.g. an upgrade): don't inject into real
                # data — just record that seeding is no longer applicable.
                _mark_seeded()
                return None
            source = sourceRepository.create_source(
                session=session,
                status="queued",
                text=WELCOME_TEXT,
                text_html=WELCOME_HTML,
                filename=WELCOME_TITLE,
                file_type="text",
            )
            source_id = source.id
        _mark_seeded()
        logger.info(f"Seeded welcome example note as source {source_id}")
        return source_id
    except Exception as exc:  # noqa: BLE001 - seeding is best-effort, never fatal
        logger.warning(f"Welcome-note seed skipped: {exc}")
        return None
