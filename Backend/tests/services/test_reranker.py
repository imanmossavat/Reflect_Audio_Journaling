from types import SimpleNamespace

from app.services import reranker


def make_node(text):
    return SimpleNamespace(node=SimpleNamespace(get_content=lambda: text))


def test_rerank_empty():
    assert reranker.rerank("q", []) == []


def test_rerank_passes_through_scores(monkeypatch):
    # Stub the cross-encoder so no weights are downloaded. predict already returns [0,1].
    monkeypatch.setattr(reranker, "_model", lambda: SimpleNamespace(predict=lambda pairs: [0.9, 0.05]))
    nodes = [make_node("relevant"), make_node("irrelevant")]
    out = reranker.rerank("q", nodes)

    assert [n for n, _ in out] == nodes  # input order preserved
    assert out[0][1] == 0.9 and out[1][1] == 0.05  # scores used as-is
