"""Extraction prompt: the second LLM call. Turns one (user message, facilitator reply) into
a JSON ExtractionDelta for state.apply_delta. Call it with ollama format="json"."""
from state import STAGE_NAMES, SessionState

# advisory criteria shown to the model for stage_ready; code (check_stage_completion) owns the gate
STAGE_CRITERIA = {
    "Description": "the user named the field, the kind of project, and at least one person involved, with concrete detail",
    "Feelings": "the user named or described at least one feeling or internal reaction in their own words",
    "Evaluation": "the user said both something that went well and something that was difficult",
    "Analysis": "the user pointed to a cause or reason behind what happened",
    "Conclusion": "the user named something they learned or realised",
    "Action Orientation": "the user named a concrete thing to try or keep noticing over the next two weeks",
}

_SCHEMA = """{
  "new_facts": [{"stage": "<one of the stages>", "text": "<close paraphrase in the user's own words>"}],
  "resolved_question_ids": ["<id of an open question the user just answered>"],
  "new_open_questions": [{"text": "<question raised this turn>", "stage": "<stage>"}],
  "context_updates": {"domain": null, "project_type": null, "stakeholders": null, "timeline": null},
  "goal_updates": {"two_week_target": null, "stated_objective": null},
  "stage_ready": false,
  "last_turn_summary": "<one sentence, max 25 words, what the USER said this turn>"
}"""

_SYSTEM = f"""You extract structured state from one turn of a reflective journaling conversation.
Return ONLY valid JSON in exactly this shape, nothing else:
{_SCHEMA}

Rules:
- Only include information the user EXPLICITLY said this turn. Do not infer, speculate, or add anything.
- Facts are close paraphrases in the user's own words, never your interpretation.
- Set a field to null or [] when there is nothing new for it.
- last_turn_summary captures what the USER said, not the facilitator, and is never empty.
- The stages, in order: {", ".join(STAGE_NAMES)}."""


def _open_questions(state: SessionState) -> str:
    rows = [f"  {q.id}: {q.text}" for q in state.open_questions if not q.resolved]
    return "\n".join(rows) if rows else "  (none)"


def build_messages(state: SessionState, user_message: str, assistant_reply: str) -> list[dict]:
    stage = state.flow.current_stage
    user = f"""Current stage: {stage}
Stage is "ready" when {STAGE_CRITERIA.get(stage, "")}.
Unresolved open questions:
{_open_questions(state)}

This turn:
User: {user_message}
Facilitator: {assistant_reply}"""
    return [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user}]
