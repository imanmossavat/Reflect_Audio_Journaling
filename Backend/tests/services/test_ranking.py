from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app.services.ranking import (
    HALF_LIFE_DAYS,
    SourceMeta,
    combined_score,
    metadata_signal,
    rank_candidates,
    recency_decay,
    tokenize_query,
)

NOW = datetime(2026, 6, 3, 12, 0, 0)


def make_node(source_id, score):
    return SimpleNamespace(
        node=SimpleNamespace(metadata={"source_id": str(source_id)}),
        score=score,
    )


# --- recency_decay --------------------------------------------------------

def test_recency_decay_now_is_one():
    assert recency_decay(NOW, NOW) == 1.0


def test_recency_decay_half_life():
    half = recency_decay(NOW - timedelta(days=HALF_LIFE_DAYS), NOW)
    assert half == pytest.approx(0.5)


def test_recency_decay_none_is_neutral():
    assert recency_decay(None, NOW) == 0.5


def test_recency_decay_future_clamped():
    assert recency_decay(NOW + timedelta(days=10), NOW) == 1.0


# --- metadata_signal ------------------------------------------------------

def test_metadata_signal_tag_overlap():
    meta = SourceMeta(tags=frozenset({"work", "deadline"}))
    terms = tokenize_query("how do I handle work pressure")
    assert metadata_signal(terms, meta) == pytest.approx(1 / 3)


def test_metadata_signal_mood_bonus():
    meta = SourceMeta(tags=frozenset({"anxious"}))
    terms = tokenize_query("when was I anxious")
    # 1 tag overlap (1/3) + mood bonus (0.3)
    assert metadata_signal(terms, meta) == pytest.approx(1 / 3 + 0.3)


def test_metadata_signal_file_type_bonus():
    meta = SourceMeta(file_type="audio", tags=frozenset())
    terms = tokenize_query("what did I say in that voice recording")
    assert metadata_signal(terms, meta) == pytest.approx(0.2)


def test_metadata_signal_empty_tags_no_penalty():
    meta = SourceMeta(tags=frozenset())
    assert metadata_signal(tokenize_query("random query"), meta) == 0.0


def test_metadata_signal_irrelevant_tags_no_penalty():
    meta = SourceMeta(tags=frozenset({"gardening", "travel"}))
    assert metadata_signal(tokenize_query("tell me about work"), meta) == 0.0


def test_metadata_signal_none_meta():
    assert metadata_signal(tokenize_query("anything"), None) == 0.0


# --- combined_score / rank_candidates ------------------------------------

def test_combined_score_weights():
    # Defaults: similarity=1.0, temporal=0.3, metadata=0.2
    assert combined_score(1.0, 1.0, 1.0) == pytest.approx(1.5)
    assert combined_score(1.0, 0.0, 0.0) == pytest.approx(1.0)


def test_similarity_dominates_by_default():
    # A: clearly more similar but old. B: recent but much less similar. A wins.
    old = NOW - timedelta(days=400)
    nodes = [make_node(1, 0.9), make_node(2, 0.1)]
    meta = {1: SourceMeta(created_at=old), 2: SourceMeta(created_at=NOW)}
    ranked = rank_candidates(nodes, meta, set(), NOW)
    assert [n.node.metadata["source_id"] for n in ranked] == ["1", "2"]


def test_recency_can_promote_near_tie():
    # Near-tie on similarity: the recent entry should be promoted over the old one.
    old = NOW - timedelta(days=400)
    nodes = [make_node(1, 0.50), make_node(2, 0.45)]
    meta = {1: SourceMeta(created_at=old), 2: SourceMeta(created_at=NOW)}
    ranked = rank_candidates(nodes, meta, set(), NOW)
    assert ranked[0].node.metadata["source_id"] == "2"


def test_rank_candidates_handles_unknown_source():
    nodes = [make_node(99, 0.5)]
    ranked = rank_candidates(nodes, {}, set(), NOW)
    assert len(ranked) == 1  # neutral metadata, still ranked, no crash


def test_rank_candidates_empty():
    assert rank_candidates([], {}, set(), NOW) == []
