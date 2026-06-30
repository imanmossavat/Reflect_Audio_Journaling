from types import SimpleNamespace

import pytest

from app.services import retrieval, generation
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
    """Stub out LlamaIndex config + SQL so ranked_retrieve is pure-ish.

    Patches target the `retrieval` module, since that is where ranked_retrieve now
    resolves these names (configure_llamaindex/get_sources_meta/reranker/_get_index)."""
    monkeypatch.setattr(retrieval, "configure_llamaindex", lambda: None)
    monkeypatch.setattr(retrieval, "get_sources_meta", lambda *a, **k: {})
    # Identity reranker: reuse the embedding score as relevance (no model load).
    monkeypatch.setattr(retrieval.reranker, "rerank", lambda question, ns: [(n, n.score) for n in ns])
    # 6 nodes so the default top_k=5 never triggers backfill unless we want it.
    nodes = [make_node(i, 1.0 - i * 0.1, f"n{i}") for i in range(6)]
    index = FakeIndex(nodes)
    monkeypatch.setattr(retrieval, "_get_index", lambda: index)
    return SimpleNamespace(monkeypatch=monkeypatch, index=index, nodes=nodes)


def test_temporal_query_builds_in_filter(patched):
    patched.monkeypatch.setattr(retrieval, "get_source_ids_in_range", lambda *a, **k: [1, 2, 3])

    retrieval.ranked_retrieve("what did I do last week", top_k=5, session=object())

    top_k_arg, filters = patched.index.calls[0]
    assert top_k_arg == 20  # max(5*OVERSAMPLE, MIN_POOL)
    assert isinstance(filters, MetadataFilters)
    f = filters.filters[0]
    assert f.key == "source_id"
    assert f.operator == FilterOperator.IN
    assert f.value == ["1", "2", "3"]  # ints converted to strings for Chroma


def test_empty_range_falls_back_to_no_filter(patched):
    patched.monkeypatch.setattr(retrieval, "get_source_ids_in_range", lambda *a, **k: [])

    retrieval.ranked_retrieve("what did I do last week", top_k=5, session=object())

    _, filters = patched.index.calls[0]
    assert filters is None  # lenient fallback: no hard filter


def test_non_temporal_query_skips_sql(patched):
    called = []
    patched.monkeypatch.setattr(
        retrieval, "get_source_ids_in_range", lambda *a, **k: called.append(1) or []
    )

    retrieval.ranked_retrieve("what makes me happy", top_k=5, session=object())

    assert called == []
    _, filters = patched.index.calls[0]
    assert filters is None


def test_result_sliced_to_top_k(patched):
    patched.monkeypatch.setattr(retrieval, "get_source_ids_in_range", lambda *a, **k: [1])

    result = retrieval.ranked_retrieve("recent stuff", top_k=3, session=object())

    assert len(result) == 3


def test_injected_identity_reranker_disables_rerank(patched):
    """The reranker_fn seam replaces the model without monkeypatching."""
    called = []
    patched.monkeypatch.setattr(retrieval, "get_source_ids_in_range", lambda *a, **k: [])
    patched.monkeypatch.setattr(
        retrieval.reranker, "rerank",
        lambda q, ns: called.append("model") or [(n, n.score) for n in ns],
    )

    retrieval.ranked_retrieve("q", top_k=5, session=object(), reranker_fn=retrieval._identity_rerank)

    assert called == []  # the cross-encoder was never invoked


def test_retrieve_nodes_delegates(monkeypatch):
    calls = []
    monkeypatch.setattr(
        retrieval, "ranked_retrieve",
        lambda question, top_k=5, session=None, modality=None, tags=None: calls.append((question, top_k)) or ["x"],
    )
    assert retrieval.retrieve_nodes("q", top_k=7) == ["x"]
    assert calls == [("q", 7)]


def test_query_sources_uses_injected_retriever_and_llm(monkeypatch):
    """query_sources synthesizes via the injected retrieve_fn + llm (no globals touched)."""
    monkeypatch.setattr(generation, "configure_llamaindex", lambda: None)
    calls = []
    fake_llm = SimpleNamespace(complete=lambda prompt: SimpleNamespace(text="the answer"))

    result = generation.query_sources(
        "my question",
        top_k=4,
        retrieve_fn=lambda question, top_k=5, modality=None, tags=None: calls.append((question, top_k)) or [],
        llm=fake_llm,
    )

    assert calls == [("my question", 4)]
    assert result["answer"] == "the answer"
    assert result["sources"] == []
