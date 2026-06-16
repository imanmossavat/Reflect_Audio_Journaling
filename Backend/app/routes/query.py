import asyncio
import datetime
from pydantic import BaseModel
import json

from app.services.rag import (
    CONTEXT_QA_TEMPLATE,
    MAX_HISTORY_MESSAGES,
    SYSTEM_PROMPT,
    build_context_str,
    check_model_installed,
    check_ollama_state,
    classify_ollama_error,
    condense_question,
    model_supports_thinking,
    query_sources,
    retrieve_nodes,
    serialize_retrieved_nodes,
    to_chat_messages,
)
from app.services.settings_service import get_setting
from app.services import chatService
from app.services import generation_registry
from app.services.ollama_gate import generation_lock, is_busy

import httpx
from ollama import AsyncClient
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse, StreamingResponse
from sqlmodel import Session

from app import logging_config
from app.db import engine, get_latest_source
from app.prompts import gibbs_facilitator_prompt
from app.prompts import tag_extraction_prompt
from app.repositories import chatRepository, tagRepository
from app.schemas.journalSchemas import (
    ExtractedTagSchema,
    ExtractedTagsResponse,
    GenerateRequest,
    QueryResponse,
    SaveAnswerRequest,
)
from database.models import Answer, Question, Source

router = APIRouter()

logger = logging_config.logger


def _ollama_host() -> str:
    return get_setting("ollama_host").rstrip("/")


def _chat_model() -> str:
    return get_setting("chat_model")


def _embed_model() -> str:
    return get_setting("embed_model")


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5
    modality: str | None = None


class QueryStreamRequest(BaseModel):
    chat_id: int
    question: str
    top_k: int = 5
    modality: str | None = None


@router.post("/query", tags=["Query"], response_model=QueryResponse)
async def query(request: QueryRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    ollama_state = check_ollama_state()
    if ollama_state == "not_installed":
        raise HTTPException(
            status_code=503,
            detail="Ollama isn't installed on your machine. Install it from https://ollama.com, then try again.",
        )
    if ollama_state == "not_running":
        raise HTTPException(
            status_code=503,
            detail="Ollama isn't running on your machine. Start it and send the message again.",
        )

    embed_model = _embed_model()
    chat_model = _chat_model()
    missing = [m for m in (embed_model, chat_model) if not check_model_installed(m)]
    if missing:
        commands = " && ".join(f"ollama pull {m}" for m in missing)
        label = "model isn't" if len(missing) == 1 else "models aren't"
        raise HTTPException(
            status_code=503,
            detail=f"The required {label} installed yet. Run `{commands}` in your terminal, then try again.",
        )

    try:
        # query_sources (LlamaIndex Settings.llm.complete) is synchronous, so run it
        # in a worker thread to keep the event loop free, and hold the generation gate
        # so it can't run a second generation alongside a streaming chat answer.
        async with generation_lock:
            result = await asyncio.to_thread(
                query_sources, request.question, top_k=request.top_k, modality=request.modality
            )
    except Exception as exc:
        kind = classify_ollama_error(exc)
        if kind == "not_running":
            raise HTTPException(
                status_code=503,
                detail="Ollama stopped while answering. Start it and send the message again.",
            ) from exc
        if kind == "model_missing":
            raise HTTPException(
                status_code=503,
                detail=f"A required Ollama model is missing. Run `ollama pull {_embed_model()}` and `ollama pull {_chat_model()}`, then try again.",
            ) from exc
        logger.exception(f"Query failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Something went wrong while answering. Check the backend logs.",
        ) from exc
    return QueryResponse(
        question=request.question,
        answer=result["answer"],
        sources=result["sources"],
        model_used=chat_model,
    )

def _sse(event_type: str, payload: dict) -> str:
    return f"data: {json.dumps({'type': event_type, **payload})}\n\n"


async def _sse_stream(events):
    """Format an async iterator of `{type, ...}` event dicts as an SSE response body.

    Events are shared across the replay buffer and every subscriber, so this must not
    mutate them — each already carries its `type`, matching the `_sse` wire shape.
    """
    async for event in events:
        yield f"data: {json.dumps(event)}\n\n"


@router.post("/query-stream", tags=["Query"])
async def query_stream(request: QueryStreamRequest):
    """Streaming version of /query.

    Starts (or re-attaches to) a background generation for the chat and streams its
    events. The generation lives in `generation_registry` and outlives this request, so
    disconnecting — navigating away or refreshing — no longer cancels or loses the answer;
    reconnect via `GET /chats/{chat_id}/generation-stream`.

    Emits SSE events of shape `{type: <event>, ...}`:
      - stage    {name: "searching" | "retrieved" | "thinking" | "writing" | "queued"}
      - thinking {delta: str}
      - token    {delta: str}
      - sources  {sources: [...]}
      - done     {model: str, message_id: int}
      - error    {detail: str}
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    generation_registry.start(
        request.chat_id, request.question, top_k=request.top_k, modality=request.modality
    )
    return StreamingResponse(
        _sse_stream(generation_registry.subscribe(request.chat_id)),
        media_type="text/event-stream",
    )


@router.get("/chats/{chat_id}/generation-stream", tags=["Query"])
async def generation_stream(chat_id: int):
    """Re-attach to an in-flight generation for `chat_id` (resume after refresh/navigate).

    Replays buffered events (so the partial answer reappears) then streams live. If no
    generation is active, emits a single `idle` event so the client falls back to a
    normal chat load.
    """
    return StreamingResponse(
        _sse_stream(generation_registry.subscribe(chat_id)),
        media_type="text/event-stream",
    )


@router.get("/generations", tags=["Query"])
async def list_generations():
    """Chats with a generation currently in progress (sidebar spinner + reconnect)."""
    return generation_registry.active()


@router.post("/extract-tags", tags=["Query"])
async def extract_tags(source_id: int) -> ExtractedTagsResponse:
    with Session(engine) as session:
        source = session.get(Source, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        if not source.text:
            raise HTTPException(status_code=422, detail="Source has no text")
        source_text = source.text

    prompt = tag_extraction_prompt.build_prompt(source_text)

    try:
        async with generation_lock, httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0)
        ) as client:
            response = await client.post(
                f"{_ollama_host()}/api/generate",
                json={
                    "model": _chat_model(),
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
                db_source = session.get(Source, source_id)
                if db_source:
                    for tag_item in tags:
                        normalised_name = tag_item.name.strip().lower()
                        if not normalised_name:
                            continue
                        tag = tagRepository.get_or_create_tag(session, name=normalised_name)
                        tagRepository.add_tag_to_source(
                            session,
                            source_id=db_source.id,
                            tag_id=tag.id,
                        )

            return ExtractedTagsResponse(tags=tags, source_text=source_text)

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
    if req.journal_text and req.journal_text.strip():
        # Frontend supplies the journal context (e.g. the user's included sources +
        # conversation), so reflection questions aren't tied to only the latest entry.
        source_text = req.journal_text
    else:
        with Session(engine) as session:
            source = get_latest_source(session)
            source_text = source.text if source else ""

    # The Gibbs reflection is a conversational facilitator. Each frontend action maps to
    # a facilitator "action": opening a stage, clarifying within it, or replying to a
    # typed answer. (focus_tag is unused for now — reflection is grounded in the included
    # sources passed as journal_text.)
    action_for_mode = {"deep_dive": "open", "clarifying": "clarify", "reply": "reply"}
    action = action_for_mode.get(getattr(req.mode, "value", req.mode))
    if action is None:
        raise HTTPException(status_code=400, detail=f"Unknown mode: {req.mode}")
    try:
        messages = gibbs_facilitator_prompt.build_messages(
            source_text,
            action=action,
            step=int(req.step) if req.step is not None else None,
            history=req.history,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    async def stream_ollama():
        try:
            async with generation_lock:
                client = AsyncClient(host=_ollama_host())
                async for chunk in await client.chat(
                    model=_chat_model(), messages=messages, stream=True, think=False
                ):
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield f"data: {json.dumps({'token': token})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Ollama streaming error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(stream_ollama(), media_type="text/event-stream")


@router.post("/save-answer", tags=["Query"])
async def save_answer(req: SaveAnswerRequest):
    now = datetime.datetime.now()
    with Session(engine) as session:
        if not session.get(Source, req.source_id):
            raise HTTPException(status_code=404, detail="Source not found")
        question = Question(
            source_id=req.source_id,
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
            r = await client.get(_ollama_host())
            return Response(
                content=r.content,
                status_code=r.status_code,
                media_type=r.headers.get("content-type", "text/plain"),
            )
    except Exception as e:
        logger.warning(f"Ollama unreachable: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "ollama": "unreachable", "error": str(e)},
        )
