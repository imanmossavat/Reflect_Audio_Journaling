import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Session, select, col

from app.db import engine
from app.routes import source, query, tags, chat, settings as settings_routes
from app import logging_config
from app.services.file_watcher import start_watcher

logger = logging_config.logger

STUCK_STATUSES = {"queued", "transcribing", "chunking", "indexing"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Re-queue any sources that were in-flight when the server last stopped
    from database.models import Source
    from app.services.sourceService import _process_source_background

    with Session(engine) as session:
        stuck = session.exec(
            select(Source).where(col(Source.status).in_(list(STUCK_STATUSES)))
        ).all()
        stuck_ids = [s.id for s in stuck if s.id is not None]

    if stuck_ids:
        logger.info(f"Re-queuing {len(stuck_ids)} stuck source(s): {stuck_ids}")
        for source_id in stuck_ids:
            asyncio.ensure_future(_process_source_background(source_id))

    observer = start_watcher()
    yield
    observer.stop()
    observer.join()


app = FastAPI(title="Source Reflection API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(source.router)
app.include_router(query.router)
app.include_router(tags.router)
app.include_router(chat.router)
app.include_router(settings_routes.router)
