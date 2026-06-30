"""The per-turn spine for the stateful loop: extraction call + state merge, gated transition.
`chat(messages) -> str` is injected, so this runs under a real model or a fake in tests."""
from typing import Callable

import extraction_prompt
from state import (
    SessionState,
    apply_delta,
    handle_extraction_failure,
    handle_thin_turn,
    is_thin_turn,
    maybe_advance,
    parse_extraction_response,
    prepare_turn,
)

Chat = Callable[[list[dict]], str]


def ingest_turn(state: SessionState, user_message: str, assistant_reply: str,
                turn: int, chat: Chat) -> SessionState:
    """Fold one (user message, facilitator reply) into state. Thin turns skip extraction."""
    prepare_turn(state, user_message)
    if is_thin_turn(user_message):
        handle_thin_turn(state, user_message, turn)
    else:
        raw = chat(extraction_prompt.build_messages(state, user_message, assistant_reply))
        delta = parse_extraction_response(raw)
        if delta is None:
            handle_extraction_failure(state, user_message, turn, raw)
        else:
            apply_delta(state, delta, turn)
    maybe_advance(state)
    return state


def play_session(state: SessionState, turns: list[dict], chat: Chat) -> list[SessionState]:
    """Replay a scripted session ([{user, assistant}, ...]). Returns a state snapshot per turn."""
    snapshots = []
    for i, t in enumerate(turns, start=1):
        ingest_turn(state, t.get("user", ""), t.get("assistant", ""), i, chat)
        snapshots.append(state.model_copy(deep=True))
    return snapshots
