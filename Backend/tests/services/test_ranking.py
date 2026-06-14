from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app.services.ranking import (
    HALF_LIFE_DAYS,
    SourceMeta,
    combined_score,
    recency_decay,
    score_candidates,
)

NOW = datetime(2026, 6, 3, 12, 0, 0)


def make_node(source_id):
    return SimpleNamespace(
        node=SimpleNamespace(metadata={"source_id": str(source_id)}),
        score=None,
    )


def rank_ids(reranked, meta, now=NOW):
    """score_candidates -> list of source_id strings, high-to-low."""
    return [s.node.node.metadata["source_id"] for s in score_candidates(reranked, meta, now)]


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


# --- combined_score -------------------------------------------------------

def test_combined_score_weights():
    # Defaults: relevance=1.0, temporal=0.3
    assert combined_score(1.0, 1.0) == pytest.approx(1.3)
    assert combined_score(1.0, 0.0) == pytest.approx(1.0)
    assert combined_score(0.0, 1.0) == pytest.approx(0.3)


# --- score_candidates -----------------------------------------------------

def test_relevance_dominates_by_default():
    # A: clearly more relevant but old. B: recent but much less relevant. A wins.
    old = NOW - timedelta(days=400)
    reranked = [(make_node(1), 0.9), (make_node(2), 0.1)]
    meta = {1: SourceMeta(created_at=old), 2: SourceMeta(created_at=NOW)}
    assert rank_ids(reranked, meta) == ["1", "2"]


def test_recency_promotes_near_tie():
    old = NOW - timedelta(days=400)
    reranked = [(make_node(1), 0.50), (make_node(2), 0.45)]
    meta = {1: SourceMeta(created_at=old), 2: SourceMeta(created_at=NOW)}
    assert rank_ids(reranked, meta)[0] == "2"


def test_handles_unknown_source():
    reranked = [(make_node(99), 0.5)]
    scored = score_candidates(reranked, {}, NOW)
    assert len(scored) == 1  # neutral recency, still ranked, no crash


def test_empty():
    assert score_candidates([], {}, NOW) == []
