import re

# Well-formed block: reasoning wrapped start-to-end.
_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
# Unclosed block: an opening tag with no matching close (e.g. generation was cut off by
# num_predict mid-thought) — everything from the tag onward is reasoning, not an answer.
_THINK_UNCLOSED = re.compile(r"<think>.*", re.DOTALL | re.IGNORECASE)
# Dangling close: a closing tag with NO opening tag at all — observed in practice from
# qwen3:30b via Ollama's /api/chat even with think=false: the response starts directly
# in reasoning text (no literal "<think>" token) and only emits "</think>" once done.
# Everything up to and including that first closing tag is still reasoning.
_THINK_DANGLING_CLOSE = re.compile(r"^.*?</think>", re.DOTALL | re.IGNORECASE)


def strip_thinking(text: str) -> str:
    """Defensive backstop for a leaked <think>...</think> reasoning block in raw model
    output. Belt-and-suspenders alongside the `think` API parameter — a fallback for
    calls where that flag isn't honored for a given model/Ollama endpoint (see
    docs/ISSUES.md, the summary-generation reasoning leak). Handles three shapes:
    a well-formed <think>...</think> pair, an unclosed opening tag (truncated
    mid-thought), and a dangling closing tag with no opening tag at all (observed from
    qwen3:30b — the opening marker never appears in `message.content`, only the close)."""
    if not text:
        return text
    stripped = _THINK_BLOCK.sub("", text)
    lowered = stripped.lower()
    if "<think>" in lowered:
        stripped = _THINK_UNCLOSED.sub("", stripped)
    elif "</think>" in lowered:
        stripped = _THINK_DANGLING_CLOSE.sub("", stripped, count=1)
    return stripped.strip()
