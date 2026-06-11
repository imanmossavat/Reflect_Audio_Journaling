"""Back-compatibility facade for the RAG pipeline.

The pipeline was split into focused, swappable modules:
  - ``prompt``       — templates + named registry (``get_prompt``)
  - ``llm_runtime``  — Ollama/LlamaIndex config + health/capability checks
  - ``retrieval``    — indexing + temporal-aware, re-ranked search
  - ``generation``   — condense + answer synthesis

This module re-exports their public symbols so existing importers
(`app.routes.query`, `app.services.sourceService`, the research scripts) keep working
with `from app.services.rag import ...`. New code should import from the specific module.
"""
from typing import Any

# Prompts ------------------------------------------------------------------------------
from app.services.prompt import (
    SYSTEM_PROMPT,
    CONTEXT_QA_TEMPLATE,
    TEXT_QA_TEMPLATE,
    CONDENSE_TEMPLATE,
    PROMPTS,
    get_prompt,
    _QA_BODY,
)

# Runtime / Ollama ---------------------------------------------------------------------
from app.services.llm_runtime import (
    check_ollama_state,
    check_model_installed,
    model_supports_thinking,
    classify_ollama_error,
    configure_llamaindex,
    _ollama_base_url,
    _embed_model,
    _llm_model,
    _thinking_enabled,
)

# Retrieval ----------------------------------------------------------------------------
from app.services.retrieval import (
    index_chunks,
    ranked_retrieve,
    retrieve_nodes,
    serialize_retrieved_nodes,
    build_context_str,
    _identity_rerank,
    _get_index,
    _chunk_metadata,
)

# Generation ---------------------------------------------------------------------------
from app.services.generation import (
    query_sources,
    condense_question,
    to_chat_messages,
    MAX_HISTORY_MESSAGES,
    CONDENSE_HISTORY_MESSAGES,
    _ROLE_TO_CHAT,
)


__all__ = [
    # prompt
    "SYSTEM_PROMPT", "CONTEXT_QA_TEMPLATE", "TEXT_QA_TEMPLATE", "CONDENSE_TEMPLATE",
    "PROMPTS", "get_prompt", "_QA_BODY",
    # llm_runtime
    "check_ollama_state", "check_model_installed", "model_supports_thinking",
    "classify_ollama_error", "configure_llamaindex", "_ollama_base_url", "_embed_model",
    "_llm_model", "_thinking_enabled",
    # retrieval
    "index_chunks", "ranked_retrieve", "retrieve_nodes", "serialize_retrieved_nodes",
    "build_context_str", "_identity_rerank", "_get_index", "_chunk_metadata",
    # generation
    "query_sources", "condense_question", "to_chat_messages", "MAX_HISTORY_MESSAGES",
    "CONDENSE_HISTORY_MESSAGES", "_ROLE_TO_CHAT",
    # dynamic (via __getattr__): OLLAMA_BASE_URL, EMBED_MODEL, LLM_MODEL
]


# Preserve the dynamic settings attributes (`rag.OLLAMA_BASE_URL` / `EMBED_MODEL` /
# `LLM_MODEL`) that the old monolith exposed via module __getattr__.
def __getattr__(name: str) -> Any:
    if name in ("OLLAMA_BASE_URL", "EMBED_MODEL", "LLM_MODEL"):
        from app.services import llm_runtime
        return getattr(llm_runtime, name)
    raise AttributeError(f"module 'app.services.rag' has no attribute {name!r}")
