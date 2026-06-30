"""Deterministic state core for the stateful Gibbs facilitator. Pure data transformation,
no LLM calls — the session schema, extraction-delta validation, stage gates, and merge rules."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ValidationError, field_validator

# gibbs stages in order; test_state asserts these match the production prompt's STAGES
STAGE_NAMES: list[str] = [
    "Description", "Feelings", "Evaluation", "Analysis", "Conclusion", "Action Orientation",
]
VALID_STAGES = set(STAGE_NAMES)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Fact(BaseModel):
    id: str
    stage: str
    text: str
    turn: int


class OpenQuestion(BaseModel):
    id: str
    text: str
    stage: str
    resolved: bool = False


class FlowState(BaseModel):
    current_stage: str
    completed_stages: list[str] = []
    stage_ready: bool = False
    user_confirmed_advance: bool = False
    turns_in_stage: int = 0


class ContextBlock(BaseModel):
    domain: Optional[str] = None
    project_type: Optional[str] = None
    stakeholders: list[str] = []
    timeline: Optional[str] = None


class Goal(BaseModel):
    two_week_target: Optional[str] = None
    stated_objective: Optional[str] = None


class SessionState(BaseModel):
    session_id: str
    version: int
    updated_at: datetime
    flow: FlowState
    context: ContextBlock
    goal: Goal
    facts: list[Fact] = []
    open_questions: list[OpenQuestion] = []
    stage_summaries: dict[str, Optional[str]]
    last_turn_summary: Optional[str] = None
    session_complete: bool = False


def new_session(session_id: Optional[str] = None) -> SessionState:
    return SessionState(
        session_id=session_id or str(uuid.uuid4()),
        version=1,
        updated_at=_now(),
        flow=FlowState(current_stage=STAGE_NAMES[0]),
        context=ContextBlock(),
        goal=Goal(),
        stage_summaries={name: None for name in STAGE_NAMES},
    )


class NewFact(BaseModel):
    stage: str
    text: str

    @field_validator("stage")
    @classmethod
    def _stage(cls, v: str) -> str:
        if v not in VALID_STAGES:
            raise ValueError(f"Invalid stage: {v}")
        return v

    @field_validator("text")
    @classmethod
    def _text(cls, v: str) -> str:
        if not v or len(v.strip()) < 3:
            raise ValueError("Fact text too short")
        return v.strip()


class NewQuestion(BaseModel):
    text: str
    stage: str


class ContextUpdate(BaseModel):
    domain: Optional[str] = None
    project_type: Optional[str] = None
    stakeholders: Optional[list[str]] = None
    timeline: Optional[str] = None


class GoalUpdate(BaseModel):
    two_week_target: Optional[str] = None
    stated_objective: Optional[str] = None


class ExtractionDelta(BaseModel):
    new_facts: list[NewFact] = []
    resolved_question_ids: list[str] = []
    new_open_questions: list[NewQuestion] = []
    context_updates: Optional[ContextUpdate] = None
    goal_updates: Optional[GoalUpdate] = None
    stage_ready: bool = False  # advisory only; code owns the gate (see apply_delta)
    last_turn_summary: str

    @field_validator("last_turn_summary")
    @classmethod
    def _summary(cls, v: str) -> str:
        if not v or len(v.strip()) < 5:
            raise ValueError("last_turn_summary must not be empty")
        if len(v.strip().split()) > 30:
            raise ValueError("last_turn_summary exceeds 30 words")
        return v.strip()


def parse_extraction_response(raw: str) -> Optional[ExtractionDelta]:
    """Parse + validate; None on any failure (caller keeps prior state, no retry)."""
    cleaned = (raw or "").strip()
    if cleaned.startswith("```"):  # strip a fence the model may add
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1]) if len(lines) >= 3 else cleaned.strip("`")
    try:
        return ExtractionDelta(**json.loads(cleaned))
    except (json.JSONDecodeError, ValidationError, TypeError):
        return None


THIN_RESPONSES = {
    "ok", "yes", "no", "maybe", "idk", "i don't know", "not sure", "nothing", "fine",
    "sure", "hmm", "yeah", "nope", "don't know", "no idea", "i guess", "alright",
    "whatever", "i don't care",
}

ADVANCE_SIGNALS = {
    "yes", "ok", "sure", "ready", "next", "proceed", "move on", "let's move",
    "continue", "go ahead", "sounds good", "let's go", "yep", "yeah let's",
}

STAGE_KEYWORDS: dict[str, object] = {
    "Feelings": [
        "felt", "feeling", "noticed", "surprised", "frustrated", "anxious", "proud",
        "uncertain", "confident", "uncomfortable", "relieved", "confused", "satisfied",
        "nervous", "excited", "disappointed",
    ],
    "Evaluation": {
        "positive": ["went well", "worked", "good", "effective", "strong", "successful",
                     "happy with", "pleased"],
        "negative": ["went wrong", "didn't work", "problem", "difficult", "weak",
                     "could have", "should have", "failed", "missed"],
    },
    "Analysis": [
        "because", "since", "due to", "led to", "resulted in", "caused", "reason",
        "therefore", "as a result", "which meant",
    ],
    "Conclusion": [
        "learned", "realise", "realize", "understand", "now i know", "insight",
        "takeaway", "next time", "in future", "i see that",
    ],
}

RETRIEVAL_KEYWORDS = {"rubric", "criteria", "requirement", "assignment", "feedback",
                      "guideline", "marking", "grade"}


def is_thin_turn(user_message: str) -> bool:
    """Known acknowledgement or <=3 words: skip extraction, nothing to capture."""
    cleaned = (user_message or "").strip().lower().rstrip(".,!?")
    if cleaned in THIN_RESPONSES:
        return True
    return len((user_message or "").strip().split()) <= 3


def check_advance_confirmation(user_message: str) -> bool:
    cleaned = (user_message or "").strip().lower().rstrip(".,!?")
    return any(signal in cleaned for signal in ADVANCE_SIGNALS)


def check_stage_completion(state: SessionState) -> bool:
    """Code-owned stage-ready check over this stage's facts. Never an LLM call."""
    stage = state.flow.current_stage
    facts = [f for f in state.facts if f.stage == stage]
    facts_text = " ".join(f.text.lower() for f in facts)

    if stage == "Description":
        return (
            state.context.domain is not None
            and state.context.project_type is not None
            and len(state.context.stakeholders) >= 1
            and len(facts) >= 2
        )
    if stage == "Feelings":
        return len(facts) >= 1 and any(kw in facts_text for kw in STAGE_KEYWORDS["Feelings"])
    if stage == "Evaluation":
        if len(facts) < 2:
            return False
        pos = STAGE_KEYWORDS["Evaluation"]["positive"]
        neg = STAGE_KEYWORDS["Evaluation"]["negative"]
        return any(k in facts_text for k in pos) and any(k in facts_text for k in neg)
    if stage == "Analysis":
        return len(facts) >= 1 and any(kw in facts_text for kw in STAGE_KEYWORDS["Analysis"])
    if stage == "Conclusion":
        return len(facts) >= 1 and any(kw in facts_text for kw in STAGE_KEYWORDS["Conclusion"])
    if stage == "Action Orientation":
        target = state.goal.two_week_target
        return target is not None and len(target.strip().split()) >= 5
    return False


def retrieval_needed(state: SessionState, user_message: str) -> bool:
    if state.flow.current_stage in ("Analysis", "Conclusion"):
        return True
    return any(kw in (user_message or "").lower() for kw in RETRIEVAL_KEYWORDS)


def is_duplicate_fact(new_text: str, existing_facts: list[Fact], stage: str) -> bool:
    """Substring match either direction within a stage."""
    new_lower = (new_text or "").lower().strip()
    for fact in existing_facts:
        if fact.stage != stage:
            continue
        existing_lower = fact.text.lower().strip()
        if new_lower in existing_lower or existing_lower in new_lower:
            return True
    return False


def apply_delta(state: SessionState, delta: ExtractionDelta, turn: int) -> SessionState:
    """Merge a validated delta. Recomputes stage_ready (code-owned, ignores delta.stage_ready)
    and does NOT transition — maybe_advance does that, so thin confirm turns advance too."""
    for nf in delta.new_facts:
        if not is_duplicate_fact(nf.text, state.facts, nf.stage):
            state.facts.append(Fact(
                id=f"fact-{len(state.facts) + 1:03d}", stage=nf.stage, text=nf.text, turn=turn,
            ))

    resolved = set(delta.resolved_question_ids)
    for q in state.open_questions:
        if q.id in resolved:
            q.resolved = True

    for nq in delta.new_open_questions:
        state.open_questions.append(OpenQuestion(
            id=f"q-{len(state.open_questions) + 1:03d}", text=nq.text, stage=nq.stage,
        ))

    if delta.context_updates:  # null means no update, never blank an existing field
        cu = delta.context_updates
        if cu.domain:
            state.context.domain = cu.domain
        if cu.project_type:
            state.context.project_type = cu.project_type
        if cu.stakeholders:
            state.context.stakeholders = cu.stakeholders
        if cu.timeline:
            state.context.timeline = cu.timeline
    if delta.goal_updates:
        gu = delta.goal_updates
        if gu.two_week_target:
            state.goal.two_week_target = gu.two_week_target
        if gu.stated_objective:
            state.goal.stated_objective = gu.stated_objective

    state.last_turn_summary = delta.last_turn_summary
    state.flow.turns_in_stage += 1
    state.flow.stage_ready = check_stage_completion(state)
    _bump(state)
    return state


def prepare_turn(state: SessionState, user_message: str) -> SessionState:
    """Pre-generation flags. Only read a confirmation once the stage is already ready,
    so an early "yes" can't skip a stage."""
    state.flow.stage_ready = check_stage_completion(state)
    state.flow.user_confirmed_advance = (
        check_advance_confirmation(user_message) if state.flow.stage_ready else False
    )
    return state


def maybe_advance(state: SessionState) -> SessionState:
    """Transition only on criteria met AND explicit confirm. Runs every turn type."""
    if state.flow.stage_ready and state.flow.user_confirmed_advance:
        state = advance_stage(state)
    return state


def advance_stage(state: SessionState) -> SessionState:
    """Summarise the completed stage, move on (or finish), reset per-stage tracking."""
    current = state.flow.current_stage
    stage_facts = [f for f in state.facts if f.stage == current]
    state.stage_summaries[current] = " ".join(f.text for f in stage_facts)
    state.flow.completed_stages.append(current)

    idx = STAGE_NAMES.index(current)
    if idx < len(STAGE_NAMES) - 1:
        state.flow.current_stage = STAGE_NAMES[idx + 1]
    else:
        state.session_complete = True

    state.flow.turns_in_stage = 0
    state.flow.stage_ready = False
    state.flow.user_confirmed_advance = False
    return state


def handle_thin_turn(state: SessionState, user_message: str, turn: int) -> SessionState:
    state.last_turn_summary = (
        f"[{state.flow.current_stage}] Student gave a brief response: "
        f"\"{(user_message or '').strip()[:80]}\". No new information captured."
    )
    state.flow.turns_in_stage += 1
    _bump(state)
    return state


def handle_extraction_failure(
    state: SessionState, user_message: str, turn: int, raw_response: str = "",
) -> SessionState:
    """Extraction unusable: fallback summary, prior state stays authoritative."""
    truncated = (user_message or "").strip()[:120]
    state.last_turn_summary = (
        f"[{state.flow.current_stage}] Student said: \"{truncated}\" — "
        f"extraction failed, no state update."
    )
    state.flow.turns_in_stage += 1
    _bump(state)
    return state


def _bump(state: SessionState) -> None:
    state.version += 1
    state.updated_at = _now()
