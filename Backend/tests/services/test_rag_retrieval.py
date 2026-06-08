from types import SimpleNamespace

import pytest

from app.services import rag
from llama_index.core.vector_stores import FilterOperator, MetadataFilters


def make_node(sid, score, node_id):
    return SimpleNamespace(
        node=SimpleNamespace(
            metadata={"source_id": str(sid)},
            node_id=node_id,
            get_content=lambda: "",
        ),
        score=score,
    )


class FakeRetriever:
    def __init__(self, nodes):
        self._nodes = nodes

    def retrieve(self, _question):
        return list(self._nodes)


class FakeIndex:
    def __init__(self, nodes):
        self._nodes = nodes
        self.calls = []  # list of (similarity_top_k, filters)

    def as_retriever(self, similarity_top_k, filters=None):
        self.calls.append((similarity_top_k, filters))
        return FakeRetriever(self._nodes)


@pytest.fixture
def patched(monkeypatch):
    """Stub out LlamaIndex config + SQL so ranked_retrieve is pure-ish."""
    monkeypatch.setattr(rag, "configure_llamaindex", lambda: None)
    monkeypatch.setattr(rag, "get_sources_meta", lambda *a, **k: {})
    # Identity reranker: reuse the embedding score as relevance (no model load).
    monkeypatch.setattr(rag.reranker, "rerank", lambda question, ns: [(n, n.score) for n in ns])
    # 6 nodes so the default top_k=5 never triggers backfill unless we want it.
    nodes = [make_node(i, 1.0 - i * 0.1, f"n{i}") for i in range(6)]
    index = FakeIndex(nodes)
    monkeypatch.setattr(rag, "_get_index", lambda: index)
    return SimpleNamespace(monkeypatch=monkeypatch, index=index, nodes=nodes)


def test_temporal_query_builds_in_filter(patched):
    patched.monkeypatch.setattr(rag, "get_source_ids_in_range", lambda *a, **k: [1, 2, 3])

    rag.ranked_retrieve("what did I do last week", top_k=5, session=object())

    top_k_arg, filters = patched.index.calls[0]
    assert top_k_arg == 20  # max(5*OVERSAMPLE, MIN_POOL)
    assert isinstance(filters, MetadataFilters)
    f = filters.filters[0]
    assert f.key == "source_id"
    assert f.operator == FilterOperator.IN
    assert f.value == ["1", "2", "3"]  # ints converted to strings for Chroma


def test_empty_range_falls_back_to_no_filter(patched):
    patched.monkeypatch.setattr(rag, "get_source_ids_in_range", lambda *a, **k: [])

    rag.ranked_retrieve("what did I do last week", top_k=5, session=object())

    _, filters = patched.index.calls[0]
    assert filters is None  # lenient fallback: no hard filter


def test_non_temporal_query_skips_sql(patched):
    called = []
    patched.monkeypatch.setattr(
        rag, "get_source_ids_in_range", lambda *a, **k: called.append(1) or []
    )

    rag.ranked_retrieve("what makes me happy", top_k=5, session=object())

    assert called == []
    _, filters = patched.index.calls[0]
    assert filters is None


def test_result_sliced_to_top_k(patched):
    patched.monkeypatch.setattr(rag, "get_source_ids_in_range", lambda *a, **k: [1])

    result = rag.ranked_retrieve("recent stuff", top_k=3, session=object())

    assert len(result) == 3


def test_retrieve_nodes_delegates(monkeypatch):
    calls = []
    monkeypatch.setattr(
        rag, "ranked_retrieve",
        lambda question, top_k=5, session=None, modality=None: calls.append((question, top_k)) or ["x"],
    )
    assert rag.retrieve_nodes("q", top_k=7) == ["x"]
    assert calls == [("q", 7)]


def test_query_sources_delegates(monkeypatch):
    calls = []
    monkeypatch.setattr(rag, "configure_llamaindex", lambda: None)
    monkeypatch.setattr(
        rag, "ranked_retrieve",
        lambda question, top_k=5, session=None, modality=None: calls.append((question, top_k)) or [],
    )
    monkeypatch.setattr(rag, "build_context_str", lambda nodes: "ctx")
    monkeypatch.setattr(rag, "serialize_retrieved_nodes", lambda nodes: [])
    # Settings.llm has a validating setter, so swap the whole Settings reference.
    monkeypatch.setattr(
        rag, "Settings",
        SimpleNamespace(llm=SimpleNamespace(complete=lambda prompt: SimpleNamespace(text="the answer"))),
    )

    result = rag.query_sources("my question", top_k=4)

    assert calls == [("my question", 4)]
    assert result["answer"] == "the answer"
