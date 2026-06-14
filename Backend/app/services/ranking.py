from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

HALF_LIFE_DAYS = 90.0  # a chunk this old contributes half the recency weight
OVERSAMPLE = 4         # candidate pool = top_k * OVERSAMPLE ...
MIN_POOL = 20          # ... but at least this many, to give re-ranking headroom
HARD_FILTER_STRICT = False  # False => empty hard range falls back to global search


@dataclass(frozen=True)
class RankWeights:
    relevance: float = 1.0
    temporal: float = 0.3


DEFAULT_WEIGHTS = RankWeights()


@dataclass
class SourceMeta:
    created_at: Optional[datetime] = None


def recency_decay(created_at: Optional[datetime], now: datetime,
                  half_life_days: float = HALF_LIFE_DAYS) -> float:
    """Exponential half-life decay in ``[0, 1]``. ``None`` -> neutral 0.5."""
    if created_at is None:
        return 0.5
    age_days = (now - created_at).total_seconds() / 86400.0
    if age_days <= 0:
        return 1.0
    return 0.5 ** (age_days / half_life_days)


def combined_score(relevance: float, temporal: float,
                   weights: RankWeights = DEFAULT_WEIGHTS) -> float:
    return weights.relevance * relevance + weights.temporal * temporal


@dataclass
class ScoreBreakdown:
    """Per-node component contributions, recorded for empirical weight tuning."""
    relevance: float  # cross-encoder relevance, [0, 1]
    temporal: float   # recency decay, [0, 1]
    total: float


@dataclass
class ScoredNode:
    node: Any
    breakdown: ScoreBreakdown


def _node_source_id(node_with_score: Any) -> Optional[int]:
    """Read the int source_id from a node, tolerating string/missing metadata."""
    try:
        raw = node_with_score.node.metadata.get("source_id")
        return int(raw)
    except (AttributeError, TypeError, ValueError):
        return None


def score_candidates(
    reranked: list[tuple[Any, float]],
    meta_by_id: dict[int, SourceMeta],
    now: datetime,
    weights: RankWeights = DEFAULT_WEIGHTS,
) -> list[ScoredNode]:
    """Blend cross-encoder relevance with recency decay and sort high-to-low.

    `reranked` is a list of ``(node, relevance)`` pairs from the reranker. Each
    node's ``.score`` is replaced with its blended total; the breakdown lets the
    caller log per-query contributions so the weights can be tuned empirically.
    """
    scored: list[ScoredNode] = []
    for node, relevance in reranked:
        meta = meta_by_id.get(_node_source_id(node))
        temporal = recency_decay(meta.created_at if meta else None, now)
        total = combined_score(relevance, temporal, weights)
        node.score = total
        scored.append(ScoredNode(node, ScoreBreakdown(relevance, temporal, total)))

    scored.sort(key=lambda s: s.breakdown.total, reverse=True)
    return scored
