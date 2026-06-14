"""
prompts.py — Claude prompts for all four pipeline stages.

Each prompt is a (system, user_template) pair.
The user_template uses .format(**kwargs) for interpolation.

All tunable values (duration, entity counts, etc.) come from config.py.
"""

import config

# ── Shared constraint injected into every system prompt ──────────────────────

_SHARED_CONSTRAINTS = """
Core constraints that apply to every stage:
- Do not add facts not present in your input.
- Stay literal and source-grounded. Do not add emotional interpretation, psychological diagnosis, or causal explanation unless the source explicitly states it.
- Return ONLY valid JSON. No markdown fences, no commentary, no extra keys.
""".strip()


# ── Stage 1: Latent World State ───────────────────────────────────────────────

STAGE1_SYSTEM = f"""
You are generating the latent world state for a synthetic personal knowledge dataset used for retrieval-augmented generation (RAG) evaluation.

{_SHARED_CONSTRAINTS}

Generate a realistic long-term life simulation for ONE primary user. The output should resemble the messy continuity of a real person's life rather than a neatly constructed fictional character profile.

Requirements:
- One primary user only.
- {config.MIN_ENTITIES}–{config.MAX_ENTITIES} recurring entities spanning work, relationships, family, logistics, finances, health, hobbies, routines, travel, digital life, and home maintenance.
- Some entities must recur across multiple domains to create retrieval ambiguity.
- Include major life events AND mundane repetitive behaviors.
- Include: dormant periods, abandoned habits, stale plans, forgotten intentions, recurring annoyances, unfinished admin tasks, minor repeated failures, emotionally irrational behavior, inconsistencies between stated intentions and actual behavior, changing priorities, and periods where little changes.
- Include competing interpretations for some events.
- Temporal requirements: explicit dates or relative timelines, temporal dependencies, facts that are later corrected or contradicted, plans that quietly disappear without resolution.
- Social coherence: entities should know each other in overlapping ways, relationships should influence unrelated domains.
- Financial and logistical realism: subscriptions, repairs, appointments, insurance, taxes, scheduling friction.

Output schema (return ONLY this JSON, no other text):
{{"user_profile": {{"name": "string","age": 0,"occupation": "string"}},"entities": [{{"entity_id": "string","name": "string","type": "string","domains": ["string"]}}],"story_arcs": [{{"arc_id": "string","title": "string","status": "active | dormant | stalled | resolved"}}],"projects": [{{"project_id": "string","title": "string","status": "string"}}],"latent_facts": [{{"fact_id": "string","description": "string"}}]}}
""".strip()

STAGE1_USER = "Generate the latent world state now."


# ── Stage 2: Event Stream ─────────────────────────────────────────────────────

STAGE2_SYSTEM = f"""
You are generating a {config.DURATION_DAYS}-day event stream from a provided latent world state, for a synthetic RAG benchmark dataset.

{_SHARED_CONSTRAINTS}

You are simulating a noisy, partially incomplete human memory system, not a narrative story.

Requirements:
- Generate events spanning exactly {config.DURATION_DAYS} days.
- Include recurring routines with realistic irregularity, cancellations, reschedules, partial completions.
- Include temporal dependencies: later events may depend on earlier ones.
- Include resurfacing forgotten tasks after delays.
- Occasionally introduce conflicting or corrected information.
- Not all arcs progress evenly — some stall, decay, or silently disappear.
- Some tasks remain perpetually unfinished.
- Avoid uniform importance distribution.
- Do not over-explain motives or convert events into psychological summaries.
- Only use entities and arc IDs defined in the provided latent world state.

latent_fact_updates must be event-specific and represent one of: reinforcement, contradiction, activation, decay, escalation, clarification.

Timestamps must be strictly increasing ISO format: YYYY-MM-DDTHH:MM:SS

Output schema (return ONLY this JSON, no other text):
{{"events": [{{"event_id": "string","timestamp": "YYYY-MM-DDTHH:MM:SS","event_type": "string","involved_entities": ["string"],"story_arc_id": "string","latent_fact_updates": ["string"],"importance": 1}}]}}
""".strip()

STAGE2_USER = "Generate the {duration_days}-day event stream from this latent world state:\n\n{world_state_json}"


# ── Stage 3: Note Generation ──────────────────────────────────────────────────

STAGE3_SYSTEM = f"""
You are converting structured events into realistic personal notes for a RAG benchmark dataset.

{_SHARED_CONSTRAINTS}

Requirements:
- Natural language, imperfect human writing style.
- Concise — sometimes partial or incomplete.
- Sometimes references prior context implicitly.
- Maintain consistency with entities and timeline from the source event.
- Do not make notes sound polished or fully resolved.
- Prefer a lived-in, messy memory-fragment style.
- Do not introduce new facts not implied by the event.
- Do not turn a note into a diagnosis, interpretation, or psychological summary.

Output schema (return ONLY this JSON, no other text, one note per event):
{{"notes": [{{"note_id": "string","timestamp": "YYYY-MM-DDTHH:MM:SS","note_type": "string","text": "string","entities": ["string"],"tags": ["string"],"latent_facts": ["string"],"story_arc_id": "string","importance": "string"}}]}}
""".strip()

STAGE3_USER = "Convert these events into personal notes:\n\n{events_json}"


# ── Stage 4: QA Generation ────────────────────────────────────────────────────

STAGE4_SYSTEM = f"""
You are generating question-answer pairs from a note corpus for a RAG benchmark dataset.

{_SHARED_CONSTRAINTS}

Requirements:
- Include a mix of reasoning types: direct_retrieval, multi_hop, temporal, contradiction, abstention, comparison.
- Questions must be answerable ONLY from the notes — no outside knowledge.
- Some questions must be deliberately unanswerable from the provided notes.
- Answers must stay literal and source-grounded. Do not upgrade a partial note into a definite conclusion.
- Do not ask for psychological causes unless notes explicitly state them.
- Avoid questions that invite broad interpretation when a literal answer is available.
- supporting_notes must list real note_ids from the corpus.
- Unanswerable questions must have an empty supporting_notes array.

reasoning_type must be one of: direct_retrieval, multi_hop, temporal, contradiction, abstention, comparison
answerability must be one of: answerable, unanswerable, partial

Output schema (return ONLY this JSON, no other text):
{{"qa_pairs": [{{"question_id": "string","question": "string","answer": "string","reasoning_type": "string","supporting_notes": ["string"],"required_hops": 0,"answerability": "string"}}]}}
""".strip()

STAGE4_USER = "Generate question-answer pairs from this note corpus:\n\n{notes_json}"
