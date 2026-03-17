from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi import Response
from pydantic import BaseModel
from enum import Enum
from typing import Annotated

from requests_cache import datetime
from sqlmodel import SQLModel, Field, Session, create_engine, select
import httpx
import json
import ollama
from pathlib import Path

from app import dictionary_question_prompt
from app import simpler_dictionary_question_prompt
from app import topic_prompt
from app import logging_config

logger = logging_config.logger

app = FastAPI(title="Journal Reflection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3.5:4b"

class JournalEntry(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    filename: str
    content: str
    test: str | None = None

class TopicEntry(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    journal_id: int = Field(foreign_key="journalentry.id")
    name: str
    summary: str
    quotes: str  # store as JSON string

class QAEntry(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    journal_id: int = Field(foreign_key="journalentry.id")
    timestamp: datetime = Field(default_factory=datetime.now)
    question: str
    answer: str

BASE_DIR = Path(__file__).resolve().parent           # Backend/app
DB_PATH = BASE_DIR.parent / "database" / "database.db"  # Backend/database/database.db
sqlite_url = f"sqlite:///{DB_PATH.as_posix()}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

class Mode(str, Enum):
    clarifying = "clarifying"
    deep_dive = "deep_dive"


class Step_N(int, Enum):
    description = 1
    feelings = 2
    evaluation = 3
    analysis = 4
    conclusion = 5
    action = 6


class Topic(BaseModel):
    name: str
    summary: str
    quotes: list[str]


class GenerateRequest(BaseModel):
    mode: Mode
    step: Step_N | None = None
    topic: str | None = None
    topic_summary: str | None = None
    history: list[dict] | None = None


class TopicResponse(BaseModel):
    topics: list[Topic]
    journal_text: str

class SaveAnswerRequest(BaseModel):
    journal_id: int
    timestamp: datetime = Field(default_factory=datetime.now)
    question: str
    answer: str

@app.post("/upload")
async def upload_journal(file: UploadFile = File(...)):
    if file.content_type != "text/plain":
        raise HTTPException(status_code=400, detail="Only plain text files are allowed.")
    content = await file.read()
    text = content.decode("utf-8")
    word_count = len(text.split())
    with Session(engine) as session:
        journal_entry = JournalEntry(content=text, filename=file.filename)
        session.add(journal_entry)
        session.commit()
        session.refresh(journal_entry)
        journal_id = journal_entry.id
    return {"word_count": word_count, "filename": file.filename, "journal_id": journal_id}


@app.get("/journal-text")
async def get_journal_text():
    try:
        with Session(engine) as session:
            journal_entry = session.exec(select(JournalEntry)).first()
            journal_text = journal_entry.content if journal_entry else None
    except Exception:
        raise HTTPException(status_code=404, detail="No journal uploaded yet.")
    if not journal_text:
        raise HTTPException(status_code=404, detail="Journal is empty.")
    return {"journal_text": journal_text}


@app.post("/topics")
async def extract_topics(journal_id: int) -> TopicResponse:
    try:
        with Session(engine) as session:
            journal_entry = session.exec(select(JournalEntry)).first()
            journal_text = journal_entry.content if journal_entry else None
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No journal uploaded yet.")

    if not journal_text:
        raise HTTPException(status_code=404, detail="Journal is empty.")

    prompt = topic_prompt.build_prompt(journal_text)

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0)
        ) as client:
            response = await client.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 1024},
                    "think": False,
                },
            )
            if response.status_code != 200:
                logger.error(f"Ollama returned non-200 status: {response.status_code}")
                raise HTTPException(status_code=500, detail="Ollama error")

            result = response.json()
            response_text = result.get("response", "").strip()
            try:
                json_start = response_text.find("[")
                json_end = response_text.rfind("]") + 1
                if json_start == -1 or json_end <= json_start:
                    raise ValueError("No JSON array found in response")

                json_str = response_text[json_start:json_end]
                raw_topics = json.loads(json_str)

                topics = [Topic(name=t.get("name", ""), summary=t.get("summary", ""), quotes=t.get("quotes", [])) for t in raw_topics]

                with Session(engine) as session:
                    for t in topics:
                        db_topic = TopicEntry(
                            journal_id=journal_id,
                            name=t.name,
                            summary=t.summary,
                            quotes=json.dumps(t.quotes),
                        )
                        session.add(db_topic)

                    session.commit()

                
                return TopicResponse(topics=topics, journal_text=journal_text)

            except (json.JSONDecodeError, ValueError, KeyError) as e:
                logger.error(f"Failed to parse Ollama topic response: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to parse topics: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error during topic extraction: {e}")
        raise HTTPException(status_code=500, detail=f"Topic extraction failed: {str(e)}")


@app.post("/generate-question")
async def generate_question(req: GenerateRequest):

    try:
        with Session(engine) as session:
            journal_entry = session.exec(select(JournalEntry)).first()
            journal_text = journal_entry.content if journal_entry else None
    except Exception:
        raise HTTPException(status_code=404, detail="No journal uploaded yet.")

    if not journal_text:
        raise HTTPException(status_code=404, detail="Session not found. Please upload your journal again.")

    try:
        messages = simpler_dictionary_question_prompt.build_messages(
            journal_text,
            mode=req.mode,
            topic=req.topic,
            topic_summary=req.topic_summary,
            step=req.step,
            history=req.history,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    async def stream_ollama():
        token_count = 0
        try:
            stream = ollama.chat(model=MODEL, messages=messages, stream=True, think=False)
            for chunk in stream:
                token = chunk.get("message", {}).get("content", "")
                if token:
                    token_count += 1
                    yield f"data: {json.dumps({'token': token})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Ollama streaming error: {e}")
            yield f"data: {json.dumps({'token': f'Error: {str(e)}'})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(stream_ollama(), media_type="text/event-stream")

@app.post("/save-answer")
async def save_answer(req: SaveAnswerRequest):
    with Session(engine) as session:
        entry = QAEntry(
            journal_id=req.journal_id,
            timestamp=req.timestamp,
            question=req.question,
            answer=req.answer,
        )
        session.add(entry)
        session.commit()
    return {"ok": True}

@app.get("/ollama-health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get("http://localhost:11434")
            return Response(
                content=r.content,
                status_code=r.status_code,
                media_type=r.headers.get("content-type", "text/plain"),
            )
    except Exception as e:
        logger.warning(f"Ollama unreachable: {e}")
        return {"status": "ok", "ollama": "unreachable", "error": str(e)}