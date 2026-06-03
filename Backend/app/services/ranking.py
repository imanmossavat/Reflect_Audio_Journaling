
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

HALF_LIFE_DAYS = 90.0  # a chunk this old contributes half the recency weight
OVERSAMPLE = 4         # candidate pool = top_k * OVERSAMPLE ...
MIN_POOL = 20          # ... but at least this many, to give re-ranking headroom
HARD_FILTER_STRICT = False  # False => empty hard range falls back to global search


@dataclass(frozen=True)
class RankWeights:
    similarity: float = 1.0
    temporal: float = 0.3
    metadata: float = 0.2


DEFAULT_WEIGHTS = RankWeights()

# Mood is a curated subset of tag names (there is no mood column).
MOOD_VOCAB = frozenset({
    "happy", "happiness", "joy", "joyful", "excited", "grateful", "hopeful",
    "calm", "content", "relaxed", "proud", "sad", "sadness", "down", "lonely",
    "depressed", "anxious", "anxiety", "stressed", "stress", "overwhelmed",
    "angry", "anger", "frustrated", "afraid", "fear", "scared", "tired",
})

# Query words that imply a source modality, mapped to Source.file_type values.
_MODALITY = {
    "audio": "audio", "voice": "audio", "recording": "audio",
    "recordings": "audio", "spoken": "audio", "said": "audio",
    "note": "text", "notes": "text", "written": "text", "wrote": "text",
    "typed": "text", "text": "text", "markdown": "markdown",
}

_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "at", "for",
    "with", "about", "is", "are", "was", "were", "be", "been", "i", "me", "my",
    "you", "your", "it", "this", "that", "what", "when", "did", "do", "does",
    "how", "why", "have", "had", "has", "as", "by", "from", "we", "us",
})

_TOKEN = re.compile(r"[a-z0-9]+")


@dataclass
class SourceMeta:
    created_at: Optional[datetime] = None
    file_type: Optional[str] = None
    tags: frozenset[str] = field(default_factory=frozenset)


def tokenize_query(question: str) -> set[str]:
    """Lowercase, split on non-alphanumerics, drop stopwords."""
    return {t for t in _TOKEN.findall((question or "").lower()) if t not in _STOPWORDS}


def recency_decay(created_at: Optional[datetime], now: datetime,
                  half_life_days: float = HALF_LIFE_DAYS) -> float:
    """Exponential half-life decay in ``[0, 1]``. ``None`` -> neutral 0.5."""
    if created_at is None:
        return 0.5
    age_days = (now - created_at).total_seconds() / 86400.0
    if age_days <= 0:
        return 1.0
    return 0.5 ** (age_days / half_life_days)


def metadata_signal(query_terms: set[str], meta: Optional[SourceMeta],
                    mood_vocab: frozenset[str] = MOOD_VOCAB) -> float:
    """Soft metadata match in ``[0, 1]`` — additive, never negative."""
    if meta is None or not query_terms:
        return 0.0

    tag_tokens: set[str] = set()
    for tag in meta.tags:
        tag_tokens.update(_TOKEN.findall(tag.lower()))
    overlap = tag_tokens & query_terms
    score = min(len(overlap), 3) / 3.0

    # Mood: the query mentions a mood word that is also one of the source's tags.
    if (tag_tokens & mood_vocab) & query_terms:
        score += 0.3

    # Modality: the query names a source type matching this source's file_type.
    wanted = {_MODALITY[t] for t in query_terms if t in _MODALITY}
    if meta.file_type and meta.file_type in wanted:
        score += 0.2

    return min(score, 1.0)


def combined_score(similarity: float, temporal: float, metadata: float,
                   weights: RankWeights = DEFAULT_WEIGHTS) -> float:
    return (
        weights.similarity * similarity
        + weights.temporal * temporal
        + weights.metadata * metadata
    )


@dataclass
class ScoreBreakdown:
    """Per-node component contributions, recorded for empirical weight tuning."""
    similarity: float  # raw embedding similarity
    temporal: float    # recency decay, [0, 1]
    metadata: float    # metadata overlap signal, [0, 1]
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
    nodes: list[Any],
    meta_by_id: dict[int, SourceMeta],
    query_terms: set[str],
    now: datetime,
    weights: RankWeights = DEFAULT_WEIGHTS,
) -> list[ScoredNode]:
    """Re-rank ``NodeWithScore`` objects, returning them paired with the
    component breakdown (sorted high-to-low by total).

    Each node's ``.score`` is also replaced with its combined total for
    transparency. The breakdown lets the caller log per-query contributions so
    the weights can be tuned empirically.
    """
    scored: list[ScoredNode] = []
    for node in nodes:
        raw = getattr(node, "score", None)
        similarity = 0.0 if raw is None else raw
        meta = meta_by_id.get(_node_source_id(node))
        temporal = recency_decay(meta.created_at if meta else None, now)
        signal = metadata_signal(query_terms, meta)
        total = combined_score(similarity, temporal, signal, weights)
        node.score = total
        scored.append(ScoredNode(node, ScoreBreakdown(similarity, temporal, signal, total)))

    scored.sort(key=lambda s: s.breakdown.total, reverse=True)
    return scored


def rank_candidates(
    nodes: list[Any],
    meta_by_id: dict[int, SourceMeta],
    query_terms: set[str],
    now: datetime,
    weights: RankWeights = DEFAULT_WEIGHTS,
) -> list[Any]:
    """Convenience wrapper returning only the re-ranked nodes (see score_candidates)."""
    return [s.node for s in score_candidates(nodes, meta_by_id, query_terms, now, weights)]
