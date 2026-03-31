import datetime
from pydantic import BaseModel
import json

from app.services.rag import query_journals

import httpx
import ollama
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from app import logging_config
from app.db import engine, get_latest_journal
from app.prompts import simpler_dictionary_question_prompt
from app.prompts import tag_extraction_prompt
from app.repositories import tagRepository
from app.schemas.journalSchemas import (
    ExtractedTagSchema,
    ExtractedTagsResponse,
    GenerateRequest,
    QueryResponse,
    SaveAnswerRequest,
)
from database.models import Answer, Journal, Question

router = APIRouter()

logger = logging_config.logger

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3.5:4b"


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5


@router.post("/query", tags=["Query"], response_model=QueryResponse)
async def query(request: QueryRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    result = query_journals(request.question, top_k=request.top_k)
    return QueryResponse(question=request.question, answer=result["answer"], sources=result["sources"])

@router.post("/extract-tags", tags=["Query"])
async def extract_tags(journal_id: int) -> ExtractedTagsResponse:
    with Session(engine) as session:
        journal = session.get(Journal, journal_id)
        if not journal:
            raise HTTPException(status_code=404, detail="Journal not found")
        if not journal.text:
            raise HTTPException(status_code=422, detail="Journal has no text")
        journal_text = journal.text

    prompt = tag_extraction_prompt.build_prompt(journal_text)

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

            json_start = response_text.find("[")
            json_end = response_text.rfind("]") + 1
            if json_start == -1 or json_end <= json_start:
                raise ValueError("No JSON array found in response")

            raw_tags = json.loads(response_text[json_start:json_end])
            tags = [
                ExtractedTagSchema(
                    name=t.get("name", ""),
                    summary=t.get("summary", ""),
                    quotes=t.get("quotes", []),
                )
                for t in raw_tags
            ]

            with Session(engine) as session:
                db_journal = session.get(Journal, journal_id)
                if db_journal:
                    for tag_item in tags:
                        normalised_name = tag_item.name.strip().lower()
                        if not normalised_name:
                            continue
                        tag = tagRepository.get_or_create_tag(session, name=normalised_name)
                        tagRepository.add_tag_to_journal(
                            session,
                            journal_id=db_journal.id,
                            tag_id=tag.id,
                        )

            return ExtractedTagsResponse(tags=tags, journal_text=journal_text)

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.error(f"Failed to parse Ollama tag response: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to parse tags: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error during tag extraction: {e}")
        raise HTTPException(status_code=500, detail=f"Tag extraction failed: {str(e)}")


@router.post("/generate-question", tags=["Query"])
async def generate_question(req: GenerateRequest):
    with Session(engine) as session:
        journal = get_latest_journal(session)
        journal_text = journal.text

    try:
        messages = simpler_dictionary_question_prompt.build_messages(
            journal_text,
            mode=req.mode,
            focus_tag=req.focus_tag,
            focus_tag_summary=req.focus_tag_summary,
            step=req.step,
            history=req.history,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    async def stream_ollama():
        try:
            stream = ollama.chat(model=MODEL, messages=messages, stream=True, think=False)
            for chunk in stream:
                token = chunk.get("message", {}).get("content", "")
                if token:
                    yield f"data: {json.dumps({'token': token})}\\n\\n"
            yield "data: [DONE]\\n\\n"
        except Exception as e:
            logger.error(f"Ollama streaming error: {e}")
            yield f"data: {json.dumps({'token': f'Error: {str(e)}'})}\\n\\n"
            yield "data: [DONE]\\n\\n"

    return StreamingResponse(stream_ollama(), media_type="text/event-stream")


@router.post("/save-answer", tags=["Query"])
async def save_answer(req: SaveAnswerRequest):
    now = datetime.datetime.utcnow()
    with Session(engine) as session:
        question = Question(
            journal_id=req.journal_id,
            question_text=req.question_text,
            created_at=now,
        )
        session.add(question)
        session.flush()  # get question.id

        answer = Answer(
            question_id=question.id,
            answer_text=req.answer_text,
            created_at=now,
        )
        session.add(answer)
        session.commit()

    return {"ok": True, "question_id": question.id, "answer_id": answer.id}


@router.get("/ollama-health", tags=["Query"])
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
