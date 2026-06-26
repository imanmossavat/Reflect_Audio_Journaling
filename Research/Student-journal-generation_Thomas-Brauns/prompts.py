"""
prompts.py — Pipeline prompts
==============================
All LLM prompts live here. Editing a prompt does not require touching
any stage file. Each prompt is a plain module-level string constant.

Prompt naming convention:
    STAGE_01_WORLD_STATE
    STAGE_02_EVENT_TIMELINE
    STAGE_04_NOTE_GENERATION
    STAGE_05_QA
"""

# ── Stage 01 — World state ────────────────────────────────────────────────────

STAGE_01_WORLD_STATE = """You are generating the hidden world state for a synthetic personal knowledge dataset used for retrieval-augmented generation (RAG) evaluation.

Generate a realistic long-term life simulation for ONE primary user.

The output should resemble the messy continuity of a real person's life rather than a neatly constructed fictional character profile.

GOALS

The dataset should support:
- longitudinal memory retrieval
- conflicting memory resolution
- temporal reasoning
- entity disambiguation
- incomplete task tracking
- evolving relationships
- mundane recurring details
- emotionally realistic inconsistencies

The simulation should feel partially unfinished, uneven, and organically evolving.

REQUIREMENTS

Core structure:
- One primary user only
- 10–20 recurring entities
- Mixture of: work, relationships, family, logistics, finances, health,
  hobbies, routines, travel, digital life, home maintenance
- Some entities should recur across multiple domains
- Some entities should overlap semantically to create retrieval ambiguity
- Include both major life events and mundane repetitive behaviors

Realism requirements:
- Not every entity should be equally important
- Include dormant or low-activity periods
- Include abandoned habits, stale plans, and forgotten intentions
- Include recurring annoyances and low-stakes routines
- Include unfinished admin tasks and minor repeated failures
- Include emotionally irrational behavior occasionally
- Include inconsistencies between stated intentions and actual behavior
- Include things the user avoids thinking about
- Include changing priorities over time

Temporal requirements:
- Include explicit dates or relative timelines
- Include temporal dependencies between events
- Some facts should later be corrected, revised, or contradicted
- Some plans should quietly disappear without resolution
- Include recurring weekly patterns with occasional disruptions
- Ensure not all story arcs peak simultaneously

Social coherence requirements:
- Entities should know each other in overlapping ways
- Relationships should influence unrelated domains
- Include mild interpersonal tensions, obligations, favors, or asymmetries
- Some entities should appear disproportionately often

Health and behavioral realism:
- Health issues should affect scheduling, mood, work, spending, or routines
- Habits should fluctuate instead of remaining perfectly consistent
- Include coping mechanisms, avoidance behaviors, or self-tracking systems

Financial/logistical realism:
- Financial anxiety should have concrete causes
- Include subscriptions, repairs, appointments, insurance, taxes, scheduling friction
- Include realistic tradeoffs between time, money, energy, and social obligations

RAG DIFFICULTY REQUIREMENTS

The world state should contain:
- overlapping contexts and recurring entities in multiple topics
- ambiguous references and evolving facts
- partially outdated beliefs and stale reminders
- repeated mentions of the same object or project over time
- realistic memory fragmentation

Avoid:
- perfectly clean timelines or overly dramatic lives
- every event being equally important
- isolated entities with no social overlap
- profiles where every detail is narratively meaningful

Return ONLY valid JSON. No markdown, no explanation, no code fences.

Schema:
{
  "user_profile": {
    "user_id": "u_001",
    "name": "...",
    "age": 0,
    "occupation": "...",
    "location": "...",
    "baseline_traits": ["..."]
  },
  "entities": [
    {
      "id": "...",
      "name": "...",
      "type": "person | place | project | object | organization | habit",
      "domains": ["..."],
      "salience": "low | medium | high",
      "notes": "..."
    }
  ],
  "story_arcs": [
    {
      "arc_id": "...",
      "title": "...",
      "status": "active | stalled | resolved | abandoned",
      "involved_entities": ["..."],
      "summary": "..."
    }
  ],
  "projects": [
    {
      "project_id": "...",
      "title": "...",
      "status": "active | paused | abandoned | completed",
      "related_entities": ["..."],
      "notes": "..."
    }
  ],
  "latent_facts": [
    {
      "fact_id": "...",
      "subject": "...",
      "relation": "...",
      "object": "...",
      "arc_id": "...",
      "confidence": "assumed | confirmed | contradicted"
    }
  ]
}"""


# ── Stage 02 — Event timeline ─────────────────────────────────────────────────

STAGE_02_EVENT_TIMELINE = """Using the provided world state and event skeletons, generate a chronological event timeline.

You are simulating a noisy, partially incomplete human memory system, not a narrative story.

The event skeletons below have their structure pre-filled (story_arc_id, involved_entities,
timestamp). You must only write the following fields for each event:
- text               : a natural-language description of what happened
- latent_fact_updates: how a latent fact changed, was reinforced, or contradicted
- importance         : integer 1–5

Do NOT change event_id, timestamp, story_arc_id, or involved_entities.

Core Requirements

Generate event text that:
- Evolves existing story arcs explicitly over time
- Includes recurring routines and meetings with realistic irregularity
- Includes cancellations, reschedules, and partial completions
- Includes temporal dependencies (later events depend on earlier ones)
- Occasionally introduces conflicting or corrected information

Realism Constraints
- Not all arcs progress evenly or continuously
- Some tasks remain perpetually unfinished
- Behavior must reflect inconsistency between intent and action
- Avoid uniform importance distribution

Latent Fact Rules (CRITICAL)
latent_fact_updates must:
- Represent a change, reinforcement, contradiction, or activation
- Be event-specific — not a repeated static fact
- NOT repeat latent facts verbatim unless explicitly recontextualized

Contradiction events (those with _contradiction_of set):
- MUST introduce a different outcome, revised fact, or changed status
  compared to the event they reference
- Do NOT simply repeat the earlier event with different wording

Return ONLY valid JSON. No markdown, no commentary, no extra keys.

{
  "events": [
    {
      "event_id": "...",
      "timestamp": "YYYY-MM-DDTHH:MM:SS",
      "event_type": "...",
      "involved_entities": ["..."],
      "story_arc_id": "...",
      "latent_fact_updates": ["..."],
      "importance": 1
    }
  ]
}"""


# ── Stage 04 — Note generation ────────────────────────────────────────────────

STAGE_04_NOTE_GENERATION = """Convert the structured event into a realistic personal note.

Requirements:
- Natural language, imperfect human writing style
- Concise, sometimes partial or incomplete
- Sometimes references prior context implicitly
- Maintain consistency with entities and timeline
- Do not make the note sound polished or fully resolved
- Prefer a lived-in, messy memory fragment style

Apply 1–3 of the following rules (pick randomly, never apply all):

OMISSION — leave out one concrete detail from the event (the person's name,
  the exact date, or the outcome). The note should feel like the writer
  didn't bother to write everything down.

ABRUPT_END — stop the note mid-thought as if the writer got distracted.
  Do not add a conclusion or summary sentence.

IMPLICIT_REFERENCE — mention something from a prior event without explaining
  it. Use phrases like "the usual thing with Marcus" or "like last time"
  without clarifying what that means.

UNCERTAINTY — express doubt about a fact: "think it was Tuesday",
  "not sure if I already replied", "might have been €200, can't remember".

LATENT_FACT_AS_TEXTURE — do not state the latent fact directly. Let it
  colour the tone instead. If the latent fact is "user is avoiding thinking
  about rent", the note might just say "didn't open the bank app again".

CRITICAL: latent_facts in the output JSON must represent a state transition,
not a summary of the event text.
Bad:  "user attended the meeting"
Good: "user now knows the deadline moved — activates the anxiety arc"

Return ONLY valid JSON:
{
  "note_id": "",
  "timestamp": "",
  "note_type": "",
  "text": "",
  "entities": [],
  "tags": [],
  "latent_facts": [],
  "story_arc_id": "",
  "importance": ""
}"""


# ── Stage 05 — QA generation ──────────────────────────────────────────────────

STAGE_05_QA = """You are generating a question-answer pair for a RAG benchmark dataset.

You are given a set of personal notes (the retrieval corpus).
The question must be answerable ONLY from these notes — no outside knowledge.

QA type: {qa_type}

Type-specific instructions:
- single_hop:          Question answerable from exactly one note. Keep it concrete.
- multi_hop:           Question that REQUIRES combining information from all notes given.
                       The answer cannot be found in any single note alone.
- temporal_reasoning:  Question whose answer depends on the ORDER of events.
                       e.g. "What changed between the first and last mention of X?"
- conflict_resolution: Two notes contradict each other. The question must ask
                       the reader to identify or resolve the contradiction.
                       e.g. "The notes give two different statuses for X — which is more recent?"
- unanswerable:        The notes hint at something but do not contain the answer.
                       The correct answer is "cannot be determined from the notes."

Notes (these are the ONLY source of truth):
{notes_text}

Rules:
- Answer must be literally supported by the notes — no inference beyond what is stated
- Do not invent facts not present in the notes
- Keep the question specific and unambiguous
- The answer should be 1–3 sentences maximum

Return ONLY valid JSON:
{{
  "question": "...",
  "answer": "...",
  "reasoning_type": "{qa_type}",
  "supporting_notes": {note_ids},
  "required_hops": {hop_count},
  "difficulty": "easy | medium | hard"
}}"""