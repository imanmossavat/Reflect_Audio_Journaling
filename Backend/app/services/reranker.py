"""BGE cross-encoder reranker. Local, multilingual, Apache-2.0; weights download on first use."""
from functools import lru_cache
from typing import Any

MODEL_NAME = "BAAI/bge-reranker-v2-m3"


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import CrossEncoder

    return CrossEncoder(MODEL_NAME)


def rerank(question: str, nodes: list[Any]) -> list[tuple[Any, float]]:
    """Score each node against the question; returns (node, relevance in [0,1]) in input order.

    CrossEncoder.predict already sigmoid-activates single-label models, so the scores are [0,1].
    """
    if not nodes:
        return []
    pairs = [(question, n.node.get_content() or "") for n in nodes]
    scores = _model().predict(pairs)
    return [(node, float(score)) for node, score in zip(nodes, scores)]
