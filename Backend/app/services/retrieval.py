"""Retrieval half of the RAG pipeline: indexing + temporal-aware, re-ranked search.

The retriever is composed of swappable pieces. `ranked_retrieve` accepts:
  - `reranker_fn`         — (question, nodes) -> [(node, relevance)]; defaults to the BGE
                            cross-encoder. Pass `_identity_rerank` to disable reranking.
  - `source_meta_provider`— (session, source_ids) -> {source_id: SourceMeta}; defaults to the
                            SQLite lookup. Pass a stub returning {} to neutralize recency (eval).
  - `weights`             — RankWeights blending relevance vs recency.
These default to production behavior, so app callers pass nothing; experiments inject
alternatives without monkeypatching. Defaults are resolved at call time (read from this
module's namespace) so existing monkeypatch-style tests keep working too.
"""
from datetime import datetime
from typing import Any, Callable

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.schema import TextNode
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters, FilterOperator
from llama_index.vector_stores.chroma import ChromaVectorStore

from sqlmodel import Session

from app.db import engine
from app.repositories.sourceRepository import get_source_ids_in_range, get_sources_meta
from app.repositories.tagRepository import get_sources_by_tags
from app.services.chroma import get_chroma_collection
from app.services import reranker
from app.services.ranking import (
    DEFAULT_WEIGHTS,
    HARD_FILTER_STRICT,
    MIN_POOL,
    OVERSAMPLE,
    RankWeights,
    _node_source_id,
    score_candidates,
)
from app.services.llm_runtime import configure_llamaindex
from app.services.temporal import parse_temporal_range
from app import logging_config

logger = logging_config.logger


def _identity_rerank(question: str, nodes: list[Any]) -> list[tuple[Any, float]]:
    """No-op reranker: reuse each node's embedding score as relevance (reranker OFF)."""
    return [(n, float(getattr(n, "score", 0.0) or 0.0)) for n in nodes]


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


def ranked_retrieve(
    question: str,
    top_k: int = 5,
    session: Session | None = None,
    modality: str | None = None,
    *,
    tags: list[str] | None = None,
    reranker_fn: Callable[[str, list[Any]], list[tuple[Any, float]]] | None = None,
    source_meta_provider: Callable[..., dict] | None = None,
    weights: RankWeights = DEFAULT_WEIGHTS,
) -> list[Any]:
    configure_llamaindex()
    # Resolve injectables at call time so module-level monkeypatching still works.
    reranker_fn = reranker_fn if reranker_fn is not None else reranker.rerank
    source_meta_provider = source_meta_provider if source_meta_provider is not None else get_sources_meta

    index = _get_index()
    now = datetime.utcnow()
    pool_k = max(top_k * OVERSAMPLE, MIN_POOL)

    owns_session = session is None
    session = session or Session(engine)
    try:
        date_range = parse_temporal_range(question, now)
        filter_list: list[MetadataFilter] = []
        # A tag scope is an explicit, hard constraint chosen by the user, so it must never
        # be backfilled with unrelated chunks (unlike the lenient temporal window below).
        allow_backfill = True
        if modality:
            filter_list.append(MetadataFilter(key="modality", value=modality, operator=FilterOperator.EQ))
        if tags:
            tag_source_ids = [s.id for s in get_sources_by_tags(session, tag_names=tags, match="any")]
            if not tag_source_ids:
                # Explicit tag scope with no matching sources: return nothing rather than
                # silently widening to untagged notes.
                return []
            filter_list.append(
                MetadataFilter(
                    key="source_id",
                    value=[str(i) for i in tag_source_ids],
                    operator=FilterOperator.IN,
                )
            )
            allow_backfill = False
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
        if filters is not None and allow_backfill and len(nodes) < top_k:
            seen = {n.node.node_id for n in nodes}
            extra = index.as_retriever(similarity_top_k=pool_k).retrieve(question)
            nodes.extend(n for n in extra if n.node.node_id not in seen)

        source_ids = [sid for sid in (_node_source_id(n) for n in nodes) if sid is not None]
        meta_by_id = source_meta_provider(session, source_ids)
        reranked = reranker_fn(question, nodes)
        scored = score_candidates(reranked, meta_by_id, now, weights)
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


def retrieve_nodes(
    question: str, top_k: int = 5, modality: str | None = None, tags: list[str] | None = None
) -> list[Any]:
    """Returns the top_k retrieved nodes for `question` without running the LLM step."""
    return ranked_retrieve(question, top_k=top_k, modality=modality, tags=tags)


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
    """Join retrieved node texts into the `{context_str}` block for the QA template."""
    return "\n\n".join((source.node.get_content() or "").strip() for source in nodes or [])
