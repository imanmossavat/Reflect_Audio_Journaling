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
from app.services import reflectionLoop
from app.services import reflectionService
from app.services import reflectionStateService
from app.services import safety
from app.services.ollama_gate import generation_lock, is_busy

import httpx
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse, StreamingResponse
from sqlmodel import Session

from app import logging_config
from app.db import engine, get_latest_source
from app.repositories import chatRepository
from app.services import tagService
from app.schemas.journalSchemas import (
    ExtractedTagSchema,
    ExtractedTagsResponse,
    GenerateRequest,
    Mode,
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


def _safety_model() -> str:
    return get_setting("safety_model")


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5
    modality: str | None = None
    # Optional tag scope: retrieval is restricted to sources carrying any of these tags.
    tags: list[str] | None = None


class QueryStreamRequest(BaseModel):
    chat_id: int
    question: str
    top_k: int = 5
    modality: str | None = None
    tags: list[str] | None = None


@router.post("/query", tags=["Query"], response_model=QueryResponse)
async def query(request: QueryRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    ollama_state = check_ollama_state()
    if ollama_state == "not_installed":
        logger.error("Query aborted: Ollama is not installed")
        raise HTTPException(
            status_code=503,
            detail="Ollama isn't installed on your machine. Install it from https://ollama.com, then try again.",
        )
    if ollama_state == "not_running":
        logger.error("Query aborted: Ollama is not running")
        raise HTTPException(
            status_code=503,
            detail="Ollama isn't running on your machine. Start it and send the message again.",
        )

    embed_model = _embed_model()
    chat_model = _chat_model()
    safety_model = _safety_model()
    # The Llama Guard model is required too: without the guardrail we can't ensure a safe
    # environment, so a missing guard model blocks sending just like chat/embed.
    missing = [m for m in (embed_model, chat_model, safety_model) if not check_model_installed(m)]
    if missing:
        logger.error("Query aborted: model(s) not installed: %s", ", ".join(missing))
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
                query_sources, request.question, top_k=request.top_k,
                modality=request.modality, tags=request.tags
            )
    except Exception as exc:
        kind = classify_ollama_error(exc)
        if kind == "not_running":
            logger.error("Query failed: Ollama stopped mid-answer: %s", exc)
            raise HTTPException(
                status_code=503,
                detail="Ollama stopped while answering. Start it and send the message again.",
            ) from exc
        if kind == "model_missing":
            logger.error("Query failed: required model went missing mid-answer: %s", exc)
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

class SafetyCheckRequest(BaseModel):
    text: str


class GroupTopicsRequest(BaseModel):
    journal_text: str


@router.post("/reflection/topics", tags=["Query"])
async def group_topics(request: GroupTopicsRequest):
    """Group the selected sources into 2-5 named topics (each with supporting excerpts)
    so the user can pick a single theme to reflect on, instead of naming it themselves."""
    try:
        async with generation_lock:
            topics = await asyncio.to_thread(reflectionService.group_topics, request.journal_text)
        return {"topics": topics}
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        raise HTTPException(status_code=502, detail=f"Could not group topics: {e}")
    except Exception as e:
        logger.exception(f"Topic grouping failed: {e}")
        raise HTTPException(status_code=500, detail="Topic grouping failed.")


@router.post("/safety/check", tags=["Safety"])
async def safety_check(request: SafetyCheckRequest):
    """Screen a user-authored snippet (used by the no-AI reflection-writing flow).

    Never blocks: returns a care `kind` ("self_harm" | "support") when the text trips a
    relevant Llama Guard category, so the UI can offer an empathetic support card.
    Fail-open by design — see `safety.classify_user_text`.
    """
    verdict = await safety.classify_user_text(request.text)
    return {"flagged": verdict.flagged, "kind": verdict.kind, "categories": verdict.categories}


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
      - stage    {name: "checking" | "searching" | "retrieved" | "thinking" | "writing" | "queued"}
      - progress {chars: int}   # buffered answer length; grows the UI skeleton (text is withheld)
      - sources  {sources: [...]}
      - done     {model: str, message_id: int}   # guard passed; client refetches & reveals
      - fallback {kind: "self_harm" | "support"}   # guard tripped; show a support card, no answer
      - guard_unavailable {model: str, command: str}   # guard model not installed; show setup card
      - error    {detail: str}
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    generation_registry.start(
        request.chat_id, request.question, top_k=request.top_k,
        modality=request.modality, tags=request.tags
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

    try:
        # Serialize against chat generation; the extraction call itself is synchronous
        # (shared with the ingest pipeline), so run it off the event loop.
        async with generation_lock:
            tags, source_text = await asyncio.to_thread(
                tagService.extract_and_store_tags, source_id, origin="llm", replace_existing=True
            )
        return ExtractedTagsResponse(
            tags=[ExtractedTagSchema(**t) for t in tags],
            source_text=source_text,
        )
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
    """The reflection turn loop (Document B §4), behind the same four-lever
    request shape the frontend already sends. `step`/`goal`/`scope_items` are
    accepted for backward compatibility but no longer drive the turn — see
    reflectionStateService (Focus persists from the chat's reflection_goal)
    and reflectionLoop (retrieve -> Ask -> thin-turn gate -> Update)."""
    with Session(engine) as session:
        chat = chatRepository.get_chat_by_id(session, req.chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")

        if req.source_ids:
            # Frontend supplies the real ids behind journal_text (the user's included
            # sources), so retrieve_units' source_id filter has something to match —
            # journal_text itself is just an opaque concatenated blob with no ids in it.
            included_sources = [
                {"source_id": str(sid), "text": req.journal_text or ""} for sid in req.source_ids
            ]
        else:
            # Backward-compat path for callers that send journal_text without
            # source_ids (older frontend build, direct API call), or send neither.
            # There is no real source_id recoverable from a concatenated text blob, so
            # fall back to the latest source rather than fabricating one from chat_id —
            # a fake source_id (str(chat_id), the previous behavior here) never matches
            # any indexed unit's real source_id and silently yields zero retrieval
            # every turn.
            source = get_latest_source(session)
            included_sources = (
                [{"source_id": str(source.id), "text": source.text}] if source and source.text else []
            )

        state = reflectionStateService.ensure_state(session, chat, included_sources)

    student_message = (req.history[-1].get("answer") or "").strip() if req.history else ""
    chat_model = _chat_model()

    async def stream_reflection_turn():
        try:
            async with generation_lock:
                if req.mode == Mode.reflect:
                    result = await asyncio.to_thread(
                        reflectionLoop.run_reflect_only,
                        state, student_message, included_sources, chat_model=chat_model,
                    )
                else:
                    resolve_hint = req.mode == Mode.deep_dive
                    result = await asyncio.to_thread(
                        reflectionLoop.run_turn,
                        state, student_message, included_sources,
                        resolve_hint=resolve_hint, chat_model=chat_model,
                    )

            # Isolated on purpose: `result.reply` was already generated successfully
            # by this point. A persistence failure here must be logged, not allowed
            # to discard that reply and report the whole turn as errored (the same
            # fix applied to generation_registry's post-RAG Update hook).
            try:
                with Session(engine) as save_session:
                    reflectionStateService.save_state(save_session, req.chat_id, result.state)
            except Exception as save_exc:
                logger.error(
                    "Chat %s: failed to persist reflection_state after a successful "
                    "reply (reply still shown, Gist/Open Thread update lost): %s",
                    req.chat_id, save_exc, exc_info=True,
                )

            if result.reply:
                yield f"data: {json.dumps({'progress': len(result.reply)})}\n\n"
                verdict = await safety.classify_ai_text(req.journal_text or "", result.reply)
                if verdict.flagged:
                    yield f"data: {json.dumps({'fallback': verdict.kind or 'support'})}\n\n"
                else:
                    # Units the reply's {{source_id:unit_id}} tokens (Document B §5) can
                    # reference — sent alongside the reply so the frontend can resolve them
                    # to citation text without a second round trip. Session-scoped only:
                    # not persisted to reflection_state or ChatMessage, so citations in a
                    # reloaded chat's history won't resolve — an accepted tradeoff, not an
                    # oversight (see the frontend rendering code for the fallback).
                    units_payload = [u.model_dump() for u in result.retrieved]
                    yield f"data: {json.dumps({'text': result.reply, 'model': chat_model, 'units': units_payload})}\n\n"
            else:
                # The "Answer" lever (mode=reflect) and a thin-turn both produce no
                # facilitator reply by design — not an error.
                yield f"data: {json.dumps({'model': chat_model})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Reflection turn error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(stream_reflection_turn(), media_type="text/event-stream")


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
        # Health probe; polled frequently and handled by the client. Not a logged failure.
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "ollama": "unreachable", "error": str(e)},
        )
