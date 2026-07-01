# In-memory registry of in-flight chat generations, decoupled from any request.

import asyncio
import json
from typing import AsyncIterator, Optional

from ollama import AsyncClient
from sqlmodel import Session

from app import logging_config
from app.db import engine
from app.repositories import chatRepository
from app.services import chatService
from app.services import reflectionLoop
from app.services import reflectionStateService
from app.services import safety
from app.services.ollama_gate import generation_lock, is_busy
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
    retrieve_nodes,
    serialize_retrieved_nodes,
    to_chat_messages,
)
from app.services.settings_service import chat_num_ctx, get_setting

logger = logging_config.logger

# How long a finished job lingers so a client reconnecting right at completion can still
# replay the final events. The answer is already in the DB by then, so this is only for a
# seamless live-resume.
_RETENTION_SECONDS = 30

_TERMINAL_TYPES = {"done", "error", "idle", "fallback", "guard_unavailable"}

# Emit a skeleton-growth tick roughly every this many answer characters. The frontend
# renders a pulsing skeleton sized to this count and never sees the real text until the
# output guard passes (see `_run`).
_PROGRESS_STEP = 20


def _ollama_host() -> str:
    return get_setting("ollama_host").rstrip("/")


def _chat_model() -> str:
    return get_setting("chat_model")


def _embed_model() -> str:
    return get_setting("embed_model")


def _safety_model() -> str:
    return get_setting("safety_model")


class GenerationJob:

    def __init__(self, chat_id: int):
        self.chat_id = chat_id
        self.status: str = "queued"  # queued | thinking | writing | done | error
        self.events: list[dict] = []  # replay buffer, in emit order
        self.subscribers: set[asyncio.Queue] = set()
        self.message_id: Optional[int] = None
        self.error_detail: Optional[str] = None
        self.task: Optional[asyncio.Task] = None

    @property
    def finished(self) -> bool:
        return self.status in ("done", "error")

    def emit(self, event_type: str, **payload) -> None:
        """Record an event and fan it out to every live subscriber."""
        event = {"type": event_type, **payload}
        self.events.append(event)
        for queue in self.subscribers:
            queue.put_nowait(event)


# chat_id -> job. Holds active jobs and recently-finished ones (until evicted).
_jobs: dict[int, GenerationJob] = {}


def get(chat_id: int) -> Optional[GenerationJob]:
    return _jobs.get(chat_id)


def active() -> list[dict]:
    """Chats with a generation still in progress (drives the sidebar + reconnect)."""
    return [
        {"chat_id": job.chat_id, "status": job.status}
        for job in _jobs.values()
        if not job.finished
    ]


def start(
    chat_id: int,
    question: str,
    top_k: int = 5,
    modality: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> GenerationJob:
    """Begin (or re-attach to) a generation for `chat_id`.    """
    existing = _jobs.get(chat_id)
    if existing is not None and not existing.finished:
        return existing

    job = GenerationJob(chat_id)
    _jobs[chat_id] = job
    job.task = asyncio.create_task(_run(job, question, top_k, modality, tags))
    return job


async def subscribe(chat_id: int) -> AsyncIterator[dict]:
    """Yield a job's events: replay what's buffered, then stream live until terminal.    """
    job = _jobs.get(chat_id)
    if job is None:
        yield {"type": "idle"}
        return

    queue: asyncio.Queue = asyncio.Queue()
    job.subscribers.add(queue)
    try:
        replay = list(job.events)
        for event in replay:
            yield event
        if replay and replay[-1]["type"] in _TERMINAL_TYPES:
            return
        while True:
            event = await queue.get()
            yield event
            if event["type"] in _TERMINAL_TYPES:
                return
    finally:
        job.subscribers.discard(queue)


async def _evict_later(chat_id: int) -> None:
    await asyncio.sleep(_RETENTION_SECONDS)
    job = _jobs.get(chat_id)
    if job is not None and job.finished:
        _jobs.pop(chat_id, None)


async def _update_reflection_state_after_rag_turn(
    chat_id: int,
    reflection_state,
    question: str,
    answer_text: str,
    sources_payload: list[dict] | None,
    chat_model: str,
) -> None:
    """The "Ask sources" mid-conversation detour feeds back into the same
    continuity mechanism as any other turn (Design Doc §1) — via an explicit
    Update call, replacing the old implicit role-matching history leak this
    detour used to rely on.

    Best-effort and isolated on purpose: by the time this runs, the RAG
    answer is already saved and about to be reported to the user as done.
    Document B's own rule for Update ("keep prior state, Ask's reply still
    goes through") only covers JSON/validation failures inside
    `run_update` itself — an unexpected exception here (e.g. Ollama
    hiccupping mid-call) must not propagate and turn an already-successful
    turn into a reported failure.
    """
    try:
        retrieved_units = [
            reflectionLoop.SourceUnit(
                source_id=str(s.get("source_id") or ""),
                unit_id=str(s.get("chunk_id") or "full"),
                text=s.get("text") or "",
            )
            for s in (sources_payload or [])
            if s.get("text")
        ]
        async with generation_lock:
            new_gist, new_open_thread, _ = await asyncio.to_thread(
                reflectionLoop.run_update,
                reflection_state, question, answer_text, retrieved_units,
                chat_model=chat_model,
            )
        reflection_state = reflection_state.model_copy(
            update={"gist": new_gist, "open_thread": new_open_thread}
        )
        with Session(engine) as session:
            reflectionStateService.save_state(session, chat_id, reflection_state)
    except Exception as update_exc:
        logger.error(
            "Chat %s: reflection Update after an 'Ask sources' turn failed "
            "(answer already saved, Gist/Open Thread left unchanged): %s",
            chat_id, update_exc, exc_info=True,
        )


async def _run(
    job: GenerationJob,
    question: str,
    top_k: int,
    modality: Optional[str],
    tags: Optional[list[str]] = None,
) -> None:
    try:
        ollama_state = check_ollama_state()
        if ollama_state == "not_installed":
            logger.error("Chat %s: cannot generate — Ollama is not installed", job.chat_id)
            job.error_detail = "Ollama isn't installed on your machine. Install it from https://ollama.com, then try again."
            job.status = "error"
            job.emit("error", detail=job.error_detail)
            return
        if ollama_state == "not_running":
            logger.error("Chat %s: cannot generate — Ollama is not running", job.chat_id)
            job.error_detail = "Ollama isn't running on your machine. Start it and send the message again."
            job.status = "error"
            job.emit("error", detail=job.error_detail)
            return

        embed_model = _embed_model()
        chat_model = _chat_model()
        missing = [m for m in (embed_model, chat_model) if not check_model_installed(m)]
        if missing:
            logger.error("Chat %s: cannot generate — model(s) not installed: %s", job.chat_id, ", ".join(missing))
            commands = " && ".join(f"ollama pull {m}" for m in missing)
            label = "model isn't" if len(missing) == 1 else "models aren't"
            job.error_detail = f"The required {label} installed yet. Run `{commands}` in your terminal, then try again."
            job.status = "error"
            job.emit("error", detail=job.error_detail)
            return

        # The Llama Guard model is mandatory: without the guardrail we can't ensure a safe
        # environment, so we don't generate. Surface it as a gentle in-chat card (not a hard
        # error) telling the user how to install it — same in-thread treatment as a support card.
        safety_model = _safety_model()
        if not check_model_installed(safety_model):
            logger.error("Chat %s: cannot generate — safety/guard model not installed: %s", job.chat_id, safety_model)
            job.status = "done"
            job.emit("guard_unavailable", model=safety_model, command=f"ollama pull {safety_model}")
            return

        # Input guardrail: screen the user's question before any retrieval or generation.
        # A self-harm question is intercepted with a support card instead of an answer — we
        # never try to "answer" it. (support-kind questions still generate: they're
        # high-false-positive and the output guard below is the backstop.)
        job.emit("stage", name="checking")
        in_verdict = await safety.classify_user_text(question)
        if in_verdict.kind == "self_harm":
            job.status = "done"
            job.emit("fallback", kind="self_harm")
            return

        supports_thinking = bool(get_setting("thinking_enabled")) and model_supports_thinking(chat_model)
        logger.debug(
            "Chat %s: starting generation model=%s thinking=%s top_k=%s",
            job.chat_id, chat_model, supports_thinking, top_k,
        )

        # Load prior conversation.
        with Session(engine) as session:
            history = to_chat_messages(chatRepository.get_messages(session, job.chat_id))
        if history and history[-1]["role"] == "user":
            history = history[:-1]
        history = history[-MAX_HISTORY_MESSAGES:]
        logger.debug("Chat %s: loaded %d history message(s)", job.chat_id, len(history))

        job.emit("stage", name="searching")
        # Conversation-aware retrieval: rewrite follow-ups into a standalone query so embeddings match the real topic.
        search_query = await asyncio.to_thread(condense_question, history, question)
        logger.debug("Chat %s: condensed query: %r → %r", job.chat_id, question, search_query)
        nodes = await asyncio.to_thread(retrieve_nodes, search_query, top_k=top_k, modality=modality, tags=tags)
        sources_payload = serialize_retrieved_nodes(nodes)
        logger.info(
            "Chat %s: retrieved %d chunk(s) | original=%r | search_query=%r:\n%s",
            job.chat_id,
            len(sources_payload),
            question,
            search_query,
            json.dumps(sources_payload, indent=2, ensure_ascii=False, default=str),
        )
        job.emit("stage", name="retrieved", count=len(nodes))

        context_str = build_context_str(nodes)
        user_turn = CONTEXT_QA_TEMPLATE.format(context_str=context_str, query_str=question)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *history,
            {"role": "user", "content": user_turn},
        ]
        logger.info(
            "ollama.chat messages (model=%s, think=%s):\n%s",
            chat_model,
            supports_thinking,
            json.dumps(messages, indent=2, ensure_ascii=False),
        )

        answer_parts: list[str] = []
        thinking_parts: list[str] = []
        wrote_writing_stage = False
        wrote_thinking_stage = False
        answer_len = 0
        emitted_chars = 0

        # Only one generation hits the model at a time.
        if is_busy():
            job.emit("stage", name="queued")
        async with generation_lock:
            job.status = "thinking"
            client = AsyncClient(host=_ollama_host())
            async for chunk in await client.chat(
                model=chat_model,
                messages=messages,
                stream=True,
                think=supports_thinking,
                options={"num_ctx": chat_num_ctx()},
            ):
                msg = chunk.get("message", {}) or {}
                thinking_delta = msg.get("thinking") or ""
                content_delta = msg.get("content") or ""

                # The real answer streams into a server-side buffer only. The client gets a
                # growing character count ("progress") to animate a skeleton, but never the
                # text — that's withheld until the output guard clears it below.
                if thinking_delta:
                    if not wrote_thinking_stage:
                        wrote_thinking_stage = True
                        job.emit("stage", name="thinking")
                    thinking_parts.append(thinking_delta)

                if content_delta:
                    if not wrote_writing_stage:
                        wrote_writing_stage = True
                        job.status = "writing"
                        job.emit("stage", name="writing")
                    answer_parts.append(content_delta)
                    answer_len += len(content_delta)
                    if answer_len - emitted_chars >= _PROGRESS_STEP:
                        emitted_chars = answer_len
                        job.emit("progress", chars=answer_len)

        if answer_len > emitted_chars:
            job.emit("progress", chars=answer_len)

        answer_text = "".join(answer_parts).strip() or "(empty response)"
        thinking_text = "".join(thinking_parts).strip() or None
        logger.debug(
            "Chat %s: generation complete — answer_len=%d thinking_len=%d",
            job.chat_id, len(answer_text), len(thinking_text or ""),
        )

        # Output guardrail: screen the AI's reply before it is ever revealed. If it trips a
        # category (e.g. jailbroken into harmful advice), swap in a support card instead of
        # showing — and persisting — the text.
        logger.debug("Chat %s: running output safety check", job.chat_id)
        out_verdict = await safety.classify_ai_text(question, answer_text)
        if out_verdict.flagged:
            job.status = "done"
            job.emit("fallback", kind=out_verdict.kind or "support")
            return

        job.emit("sources", sources=sources_payload)

        with Session(engine) as session:
            snapshot = chatService.append_message(
                session,
                job.chat_id,
                role="question",
                text=answer_text,
                model=chat_model,
                thinking=thinking_text,
                sources=sources_payload or None,
            )
            # If this chat is already in the structured reflection flow (has a
            # reflection_state row), the "Ask sources" mid-conversation detour feeds
            # back into the same continuity mechanism as any other turn (Design Doc
            # §1) — via an explicit Update call now, replacing the old implicit
            # role-matching history leak this same detour used to rely on.
            reflection_state = reflectionStateService.load_state(session, job.chat_id)

        if reflection_state is not None:
            await _update_reflection_state_after_rag_turn(
                job.chat_id, reflection_state, question, answer_text, sources_payload, chat_model,
            )

        job.message_id = snapshot["id"]
        job.status = "done"
        job.emit("done", model=chat_model, message_id=snapshot["id"])
    except Exception as exc:
        kind = classify_ollama_error(exc)
        if kind == "not_running":
            logger.error("Chat %s: Ollama stopped mid-generation: %s", job.chat_id, exc)
            detail = "Ollama stopped while answering. Start it and send the message again."
        elif kind == "model_missing":
            logger.error("Chat %s: required model went missing mid-generation: %s", job.chat_id, exc)
            detail = f"A required Ollama model is missing. Run `ollama pull {_embed_model()}` and `ollama pull {_chat_model()}`, then try again."
        else:
            logger.exception(f"Query generation failed: {exc}")
            detail = "Something went wrong while answering. Check the backend logs."
        job.error_detail = detail
        job.status = "error"
        job.emit("error", detail=detail)
    finally:
        asyncio.create_task(_evict_later(job.chat_id))
