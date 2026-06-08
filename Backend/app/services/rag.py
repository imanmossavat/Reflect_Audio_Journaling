import shutil
from datetime import datetime

import httpx
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.core.schema import TextNode
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters, FilterOperator
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.core.prompts import PromptTemplate

from typing import Any

from sqlmodel import Session

from app.db import engine
from app.repositories.sourceRepository import get_source_ids_in_range, get_sources_meta
from app.services.chroma import get_chroma_collection
from app.services import reranker
from app.services.ranking import (
    HARD_FILTER_STRICT,
    MIN_POOL,
    OVERSAMPLE,
    _node_source_id,
    score_candidates,
)
from app.services.settings_service import get_setting
from app.services.temporal import parse_temporal_range
from app import logging_config

logger = logging_config.logger


def _ollama_base_url() -> str:
    return get_setting("ollama_host").rstrip("/")


def _embed_model() -> str:
    return get_setting("embed_model")


def _llm_model() -> str:
    return get_setting("chat_model")


# WARNING: `from at pp.services.rag imporEMBED_MODEL` binds the value at import time
# and won't reflect later settings changes. Use `rag.EMBED_MODEL` (module attribute access)
# or call get_setting() directly where a fresh value is needed.
def __getattr__(name: str) -> Any:
    if name == "OLLAMA_BASE_URL":
        return _ollama_base_url()
    if name == "EMBED_MODEL":
        return _embed_model()
    if name == "LLM_MODEL":
        return _llm_model()
    raise AttributeError(f"module 'app.services.rag' has no attribute {name!r}")


def check_ollama_state() -> str:
    try:
        with httpx.Client(timeout=3.0) as client:
            client.get(_ollama_base_url())
        return "ok"
    except httpx.ConnectError:
        return "not_running" if shutil.which("ollama") else "not_installed"
    except Exception:
        return "not_running"


def check_model_installed(model: str) -> bool:
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{_ollama_base_url()}/api/tags")
            response.raise_for_status()
            installed = {m.get("name", "") for m in response.json().get("models", [])}
        return any(name == model or name.startswith(f"{model}:") for name in installed)
    except Exception:
        return True 


_thinking_capability_cache: dict[tuple[str, str], bool] = {}


def model_supports_thinking(model: str) -> bool:
    # Returns True if Ollama reports the model has the 'thinking' capability.
    host = _ollama_base_url()
    key = (host, model)
    if key in _thinking_capability_cache:
        return _thinking_capability_cache[key]
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.post(f"{host}/api/show", json={"model": model})
            r.raise_for_status()
            supports = "thinking" in (r.json().get("capabilities") or [])
    except Exception:
        supports = False
    _thinking_capability_cache[key] = supports
    return supports


def classify_ollama_error(exc: Exception) -> str:
    # Returns 'not_running', 'model_missing', or 'unknown' based on the exception.
    msg = str(exc).lower()
    connection_markers = (
        "connection refused",
        "11434",
        "all connection attempts failed",
        "winerror 10061",
        "connecterror",
        "connect call failed",
        "connection error",
        "remoteprotocolerror",
        "max retries exceeded",
    )
    if any(marker in msg for marker in connection_markers):
        return "not_running"
    if "not found" in msg or "try pulling" in msg or "pull it first" in msg or "no such model" in msg:
        return "model_missing"
    return "unknown"

TEXT_QA_TEMPLATE = PromptTemplate("""
Context information is below.
    ---------------------
    {context_str}\
    ---------------------
    You are answering questions about a journal.
    The journal entries are the source of truth.\n
    RULE PRIORITY:
    1. First-person journal entries refer to the journal author.
    2. First-person content is always valid evidence.\n
    RULES:
    1. Use only information explicitly stated in the journal entries.
    Do not add interpretation, psychological explanations, personality traits,
    motivations, or behavioral patterns unless explicitly stated.\n
    2. Do not generalize from single events into traits or habits.\n
    3. Do not convert past events into general or permanent states.\n
    4. If multiple notes are relevant, combine them into a single answer.
    Do not treat each note in isolation if they refer to related events,
    people, or timelines.\n
    5. If the notes contain information relevant to the question, you MUST answer
    using it. Answer even if the evidence is indirect, partial, or spread across
    several notes -- combine what is there. Do not refuse just because the answer
    is incomplete or not stated word-for-word.\n
    6. Refuse ONLY when NOTHING in the context bears on the question. In that single
    case, respond with EXACTLY:
    I don't know based on the notes.\n
    No explanation, no punctuation, no extra text.\n
    7. Always use 'you' and 'your' in your response when referring to the journal author.
    Do NOT use 'I' or 'me'. \n
    Question: {query_str}
    Answer:
"""
    
)

_llamaindex_signature: tuple[str, str, str] | None = None


def configure_llamaindex() -> None:
    global _llamaindex_signature
    embed = _embed_model()
    llm = _llm_model()
    host = _ollama_base_url()
    signature = (embed, llm, host)
    if _llamaindex_signature == signature:
        return
    Settings.embed_model = OllamaEmbedding(
        model_name=embed,
        base_url=host,
    )
    Settings.llm = Ollama(
        model=llm,
        base_url=host,
        request_timeout=6700.0,
        temperature=0.0,
    )
    _llamaindex_signature = signature


configure_llamaindex()


def _get_index() -> VectorStoreIndex:
    collection = get_chroma_collection()
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    return VectorStoreIndex.from_vector_store(
        vector_store, storage_context=storage_context
    )

def _chunk_metadata(chunk: dict) -> dict[str, Any]:
    """Node metadata for a chunk; created_at_ts/modality stamped when present (Chroma rejects None)."""
    metadata: dict[str, Any] = {"source_id": chunk["source_id"], "chunk_id": chunk["id"]}
    if chunk.get("created_at_ts") is not None:
        metadata["created_at_ts"] = int(chunk["created_at_ts"])
    if chunk.get("modality") is not None:
        metadata["modality"] = chunk["modality"]
    return metadata


def index_chunks(chunks: list[dict]):
    configure_llamaindex()
    collection = get_chroma_collection()
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    nodes = [
        TextNode(
            text=c["text"],
            id_=str(c["id"]),
            metadata=_chunk_metadata(c),
        )
        for c in chunks
    ]

    VectorStoreIndex(nodes, storage_context=storage_context)

def ranked_retrieve(question: str, top_k: int = 5, session: Session | None = None,
                    modality: str | None = None) -> list[Any]:
    configure_llamaindex()
    index = _get_index()
    now = datetime.utcnow()
    pool_k = max(top_k * OVERSAMPLE, MIN_POOL)

    owns_session = session is None
    session = session or Session(engine)
    try:
        date_range = parse_temporal_range(question, now)
        filter_list: list[MetadataFilter] = []
        if modality:
            filter_list.append(MetadataFilter(key="modality", value=modality, operator=FilterOperator.EQ))
        if date_range and date_range.hard:
            ids = get_source_ids_in_range(session, date_range.start, date_range.end)
            if ids:
                filter_list.append(
                    MetadataFilter(
                        key="source_id",
                        value=[str(i) for i in ids],
                        operator=FilterOperator.IN,
                    )
                )
            elif HARD_FILTER_STRICT:
                # No in-range sources and strict mode: honor the window literally.
                return []
            # Lenient (default): fall through; soft recency decay still floats recent entries up.

        filters = MetadataFilters(filters=filter_list) if filter_list else None
        nodes = index.as_retriever(similarity_top_k=pool_k, filters=filters).retrieve(question)

        # Backfill a sparse filtered pool with unfiltered hits so we never truncate below top_k; recency decay keeps in-range items on top.
        if filters is not None and len(nodes) < top_k:
            seen = {n.node.node_id for n in nodes}
            extra = index.as_retriever(similarity_top_k=pool_k).retrieve(question)
            nodes.extend(n for n in extra if n.node.node_id not in seen)

        source_ids = [sid for sid in (_node_source_id(n) for n in nodes) if sid is not None]
        meta_by_id = get_sources_meta(session, source_ids)
        reranked = reranker.rerank(question, nodes)
        scored = score_candidates(reranked, meta_by_id, now)
        _log_ranking(question, scored)
        return [s.node for s in scored[:top_k]]
    finally:
        if owns_session:
            session.close()


def _log_ranking(question: str, scored: list[Any]) -> None:
    """Log per-query component contributions (relevance / time) for empirical weight tuning."""
    breakdown = " | ".join(
        f"src={s.node.node.metadata.get('source_id')} "
        f"total={s.breakdown.total:.3f}"
        f"[rel={s.breakdown.relevance:.3f} "
        f"time={s.breakdown.temporal:.3f}]"
        for s in scored
    )
    logger.info("rerank %r -> %s", question[:80], breakdown)


def retrieve_nodes(question: str, top_k: int = 5, modality: str | None = None) -> list[Any]:
    """Returns the top_k retrieved nodes for `question` without running the LLM step."""
    return ranked_retrieve(question, top_k=top_k, modality=modality)


def serialize_retrieved_nodes(nodes: list[Any]) -> list[dict[str, Any]]:
    """Serialize retriever results into the same shape `query_sources` returns under `sources`."""
    sources = []
    for source in nodes or []:
        node = source.node
        metadata = node.metadata or {}
        sources.append(
            {
                "source_id": metadata.get("source_id"),
                "chunk_id": metadata.get("chunk_id"),
                "score": source.score,
                "node_id": node.node_id,
                "text": node.get_content(),
            }
        )
    return sources


def build_context_str(nodes: list[Any]) -> str:
    """Join retrieved node texts into the `{context_str}` block for TEXT_QA_TEMPLATE."""
    return "\n\n".join((source.node.get_content() or "").strip() for source in nodes or [])


def query_sources(question: str, top_k: int = 5, modality: str | None = None) -> dict[str, Any]:
    """Retrieve (temporal-aware, re-ranked) then synthesize an answer.

    Shares the retrieval + ranking path with the streaming route via
    ranked_retrieve, so both routes rank identically.
    """
    configure_llamaindex()
    nodes = ranked_retrieve(question, top_k=top_k, modality=modality)
    context_str = build_context_str(nodes)
    prompt = TEXT_QA_TEMPLATE.format(context_str=context_str, query_str=question)
    answer_text = Settings.llm.complete(prompt).text

    return {
        "answer": answer_text,
        "sources": serialize_retrieved_nodes(nodes),
    }