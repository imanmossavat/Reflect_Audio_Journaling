"""Thin-turn detection: identifies user messages too short to extract meaning from.

On a thin turn the generation call still runs with fallback prompt instructions,
but the extraction step is skipped and a fallback summary is written instead.
"""

_THIN_RESPONSES: frozenset[str] = frozenset({
    "ok", "okay", "yes", "no", "maybe", "idk", "i don't know", "not sure",
    "nothing", "fine", "sure", "hmm", "yeah", "nope", "don't know",
    "no idea", "i guess", "alright", "whatever", "i don't care",
    "good", "bad", "right", "yep", "nah", "mhm", "uh huh",
})


def is_thin_turn(text: str) -> bool:
    """Return True when the user's message carries too little content to extract from.

    A message is thin when:
    - it is empty, or
    - its normalised form matches a known low-information phrase, or
    - it contains three words or fewer.

    Three-word messages occasionally carry real content ("my team disagreed").
    When that happens the next generation turn will ask a follow-up and
    the subsequent extraction will capture the elaboration — so the cost of
    skipping extraction here is low.
    """
    if not text or not text.strip():
        return True
    cleaned = text.strip().lower().rstrip(".,!?")
    if cleaned in _THIN_RESPONSES:
        return True
    return len(text.strip().split()) <= 3
