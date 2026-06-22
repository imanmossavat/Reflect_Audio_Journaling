"""Generation half of the RAG pipeline: condense follow-ups, synthesize an answer.

`query_sources` accepts swappable pieces — `prompt` (the QA template), `llm` (the model
that synthesizes), and `retrieve_fn` (the retriever). All default to production behavior,
so app callers pass nothing; experiments inject alternatives without monkeypatching.
"""
from typing import Any, Callable

import ollama
from llama_index.core import Settings
from llama_index.core.prompts import PromptTemplate

from app.services.prompt import TEXT_QA_TEMPLATE, CONDENSE_TEMPLATE
from app.services.retrieval import (
    ranked_retrieve,
    build_context_str,
    serialize_retrieved_nodes,
)
from app.services.llm_runtime import configure_llamaindex, _llm_model
from app import logging_config

logger = logging_config.logger


# Map persisted chat roles to standard chat-completion roles. A user turn is stored
# as "answer" and an assistant turn as "question" (legacy reflection-mode naming).
_ROLE_TO_CHAT = {"answer": "user", "question": "assistant"}

# Cap how much history we replay so small local models keep budget for the notes.
MAX_HISTORY_MESSAGES = 12
CONDENSE_HISTORY_MESSAGES = 6


def to_chat_messages(records: list[Any]) -> list[dict[str, str]]:
    """Map persisted ChatMessage rows to user/assistant chat messages.

    Duck-typed on `.role`/`.text` so it doesn't import the DB model. Empty-text
    rows (e.g. scale-only reflection answers) are skipped.
    """
    messages: list[dict[str, str]] = []
    for record in records:
        role = _ROLE_TO_CHAT.get(getattr(record, "role", ""))
        text = (getattr(record, "text", "") or "").strip()
        if role and text:
            messages.append({"role": role, "content": text})
    return messages


def _format_history_for_condense(history: list[dict[str, str]]) -> str:
    lines = []
    for message in history[-CONDENSE_HISTORY_MESSAGES:]:
        speaker = "User" if message["role"] == "user" else "Assistant"
        lines.append(f"{speaker}: {message['content']}")
    return "\n".join(lines)


def condense_question(history: list[dict[str, str]], question: str) -> str:
    """Rewrite a follow-up into a standalone retrieval query using recent history.

    Returns the original question unchanged when there is no prior history or the
    rewrite fails, so retrieval never breaks because of the condense step.
    """
    if not history:
        return question
    prompt = CONDENSE_TEMPLATE.format(
        history_str=_format_history_for_condense(history),
        question=question,
    )
    try:
        response = ollama.chat(
            model=_llm_model(),
            messages=[{"role": "user", "content": prompt}],
            stream=False,
            think=False,
            options={"temperature": 0.0},
        )
        rewritten = ((response.get("message") or {}).get("content") or "").strip()
        if rewritten:
            logger.info("condense %r -> %r", question[:80], rewritten[:80])
            return rewritten
    except Exception as exc:
        logger.warning(f"Query condensing failed, using raw question: {exc}")
    return question


def query_sources(
    question: str,
    top_k: int = 5,
    modality: str | None = None,
    tags: list[str] | None = None,
    *,
    prompt: PromptTemplate | None = None,
    llm: Any | None = None,
    retrieve_fn: Callable[..., list[Any]] | None = None,
) -> dict[str, Any]:
    """Retrieve (temporal-aware, re-ranked) then synthesize an answer.

    Shares the retrieval + ranking path with the streaming route via the injected
    `retrieve_fn` (default `ranked_retrieve`), so both routes rank identically.
    `prompt` (default TEXT_QA_TEMPLATE) and `llm` (default Settings.llm) are swappable
    for experimentation.
    """
    configure_llamaindex()
    retrieve_fn = retrieve_fn if retrieve_fn is not None else ranked_retrieve
    prompt = prompt if prompt is not None else TEXT_QA_TEMPLATE
    llm = llm if llm is not None else Settings.llm

    nodes = retrieve_fn(question, top_k=top_k, modality=modality, tags=tags)
    context_str = build_context_str(nodes)
    prompt_str = prompt.format(context_str=context_str, query_str=question)
    answer_text = llm.complete(prompt_str).text

    return {
        "answer": answer_text,
        "sources": serialize_retrieved_nodes(nodes),
    }
