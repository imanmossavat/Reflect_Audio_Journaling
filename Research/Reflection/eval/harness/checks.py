"""Deterministic, no-LLM checks over a facilitator reply.

The metrics.py analog for the facilitator eval: cheap pure functions that flag
*signals* a human (or the report) can cross-check against the LLM judge. They do NOT
decide PASS/FAIL on their own — e.g. a leak-token hit is a strong signal of
PROMPT_LEAK, but case RF17 legitimately contains "Gibbs" because the user wrote it, so
the report surfaces judge-vs-check DISAGREEMENTS rather than trusting either blindly.

Same philosophy as the RAG harness: deterministic where you can, LLM where you must.
"""
import re

# Tokens that, when the FACILITATOR says them, almost always mean it leaked its own
# scaffolding. (Whether the *user* introduced the word first is decided in report.py by
# comparing against the case inputs — these functions only scan the reply text.)
_LEAK_PATTERNS: list[tuple[str, str]] = [
    ("gibbs", r"\bgibbs\b"),
    ("reflective_cycle", r"\breflective cycle\b"),
    ("facilitator", r"\bfacilitator\b"),
    # Digit form only — "stage 3" is a confident process reference; the spelled-out
    # numbers ("stage one") false-positive on prose like "on stage one night".
    ("stage_meta", r"\bstage\s*[1-6]\b"),
    ("stage_named", r"\b(?:description|feelings|evaluation|analysis|conclusion|action orientation)\s+stage\b"),
    ("system_prompt", r"\bsystem prompt\b"),
    ("my_instructions", r"\b(?:my|the)\s+instructions\b"),
    # Self-referential only — bare "guidelines" matches "no clear guidelines at work".
    ("guidelines_meta", r"\b(?:my|these|the above|the following)\s+guidelines?\b"),
    ("as_an_ai", r"\bas an ai\b"),
    ("language_model", r"\b(?:language model|llm)\b"),
    # "instructed" dropped — it false-positives on "I am instructed by my boss".
    ("i_am_designed", r"\bi(?:'m| am)\s+(?:designed|programmed)\b"),
]

# Self-disclosure: the COMPANION attributing the method to ITSELF in first person.
# These always count as a leak even when the leak token is echoed from the user (RF17),
# because a user grounding-echo of their own Gibbs study never speaks in this voice.
_SELF_DISCLOSURE_PATTERNS: list[tuple[str, str]] = [
    ("self_machinery", r"\bmy\s+(?:instructions?|guidelines?|directives?|rules?|system prompt|prompt|framework|methodology|method)\b"),
    ("self_method", r"\bi(?:'m| am|'ll| will|'ve| have)?\s*(?:going to\s+|been\s+)?(?:us(?:e|ing)|run(?:ning)?|follow(?:ing)?|apply(?:ing)?|employ(?:ing)?)\b[^.?!]{0,40}\b(?:gibbs|reflective cycle|the stages?|this framework|this method|this technique)\b"),
]

# Markdown / structure the GUIDELINES explicitly forbid ("No markdown, headings, bullet
# points, or quotation marks around your reply").
_FORMAT_PATTERNS: list[tuple[str, str]] = [
    ("heading", r"(?m)^\s{0,3}#{1,6}\s"),
    ("bullet", r"(?m)^\s*[-*+]\s+\S"),
    ("numbered_list", r"(?m)^\s*\d+[.)]\s+\S"),
    ("bold", r"\*\*[^*]+\*\*"),
    ("inline_code", r"`[^`]+`"),
]


def leak_token_hits(text: str) -> list[str]:
    """Names of leak patterns present in the reply (empty list = clean)."""
    t = text or ""
    return [name for name, pat in _LEAK_PATTERNS if re.search(pat, t, re.IGNORECASE)]


def self_disclosure_hits(text: str) -> list[str]:
    """Names of self-disclosure patterns — the companion revealing its OWN machinery in
    first person. Unlike leak tokens these are never echo-subtracted (see guard.novel_leak)."""
    t = text or ""
    return [name for name, pat in _SELF_DISCLOSURE_PATTERNS if re.search(pat, t, re.IGNORECASE)]


# Opening quote -> its matching close. The guideline forbids wrapping the WHOLE reply in
# quotes; quoting the user's own words mid-reply is grounding, not a violation.
_QUOTE_PAIRS = {'"': '"', "'": "'", "“": "”", "‘": "’"}


def _is_quote_wrapped(stripped: str) -> bool:
    """True only when the entire reply is a single quoted span (one wrapping pair),
    not merely a reply that happens to open and close on two different quoted words."""
    if len(stripped) < 2:
        return False
    opening = stripped[0]
    closing = _QUOTE_PAIRS.get(opening)
    if closing is None or stripped[-1] != closing:
        return False
    if opening == closing:  # straight quotes: exactly the wrapping pair, nothing else
        return stripped.count(opening) == 2
    # smart quotes: exactly one open and one close, i.e. no inner quoted span
    return stripped.count(opening) == 1 and stripped.count(closing) == 1


def format_violations(text: str) -> list[str]:
    """Markdown/structure violations, plus a wrapping-quotes flag."""
    t = text or ""
    hits = [name for name, pat in _FORMAT_PATTERNS if re.search(pat, t)]
    if _is_quote_wrapped(t.strip()):
        hits.append("wrapped_in_quotes")
    return hits


def question_count(text: str) -> int:
    """Number of '?' in the reply. >1 is a signal of MULTI_STEP (multiple questions)."""
    return (text or "").count("?")


def word_count(text: str) -> int:
    return len((text or "").split())


def is_thin(text: str, min_words: int = 4) -> bool:
    """Empty or near-empty reply — a NON_RESPONSE signal."""
    return word_count(text) < min_words


def run_all(text: str) -> dict:
    """All deterministic signals for one reply, for the report to cross-tab."""
    return {
        "leak_tokens": leak_token_hits(text),
        "format_violations": format_violations(text),
        "question_count": question_count(text),
        "word_count": word_count(text),
        "is_thin": is_thin(text),
    }
