"""Tests for Contract §8's per-unit retrieval: source_id hard-scoping (not
chat_id-stamped metadata — see retrieve_units' docstring for the reasoning)
and the "kind": "unit" separation from existing chunk nodes in the same
Chroma collection. Mirrors tests/services/test_rag_retrieval.py's FakeIndex
pattern for ranked_retrieve."""
from types import SimpleNamespace

import pytest

from app.services import retrieval
from llama_index.core.vector_stores import FilterOperator


def make_unit_node(source_id, unit_id, text):
    return SimpleNamespace(
        node=SimpleNamespace(
            metadata={"source_id": source_id, "unit_id": unit_id, "kind": "unit"},
            get_content=lambda: text,
        ),
    )


class FakeRetriever:
    def __init__(self, nodes):
        self._nodes = nodes

    def retrieve(self, _query):
        return list(self._nodes)


class FakeIndex:
    def __init__(self, nodes):
        self._nodes = nodes
        self.calls = []

    def as_retriever(self, similarity_top_k, filters=None):
        self.calls.append((similarity_top_k, filters))
        return FakeRetriever(self._nodes)


@pytest.fixture
def patched(monkeypatch):
    monkeypatch.setattr(retrieval, "configure_llamaindex", lambda: None)
    nodes = [make_unit_node("1", "p0", "first paragraph"), make_unit_node("1", "p1", "second paragraph")]
    index = FakeIndex(nodes)
    monkeypatch.setattr(retrieval, "_get_index", lambda: index)
    return SimpleNamespace(monkeypatch=monkeypatch, index=index, nodes=nodes)


def test_retrieve_units_filters_by_kind_and_source_id(patched):
    retrieval.retrieve_units("what happened", source_ids=["1", "2"], top_k=3)

    top_k, filters = patched.index.calls[0]
    assert top_k == 3
    by_key = {f.key: f for f in filters.filters}
    assert by_key["kind"].value == "unit"
    assert by_key["kind"].operator == FilterOperator.EQ
    assert by_key["source_id"].value == ["1", "2"]
    assert by_key["source_id"].operator == FilterOperator.IN


def test_retrieve_units_returns_empty_for_no_source_ids(patched):
    assert retrieval.retrieve_units("q", source_ids=[]) == []
    assert patched.index.calls == []  # never even touches the index


def test_serialize_unit_nodes_shapes_for_reflectionLoop():
    nodes = [make_unit_node("1", "p0", "first paragraph")]
    serialized = retrieval.serialize_unit_nodes(nodes)
    assert serialized == [{"source_id": "1", "unit_id": "p0", "text": "first paragraph"}]


def test_serialize_unit_nodes_handles_empty_list():
    assert retrieval.serialize_unit_nodes([]) == []
    assert retrieval.serialize_unit_nodes(None) == []
