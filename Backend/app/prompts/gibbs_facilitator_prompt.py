STAGES: dict[int, dict[str, str]] = {
    1: {
        "name": "Description",
        "goal": "describe concrete experiences, situations, or moments",
    },
    2: {
        "name": "Feelings",
        "goal": "name or describe their internal experience, if they wish",
    },
    3: {
        "name": "Evaluation",
        "goal": "say what worked well and what felt challenging or unsatisfying",
    },
    4: {
        "name": "Analysis",
        "goal": "notice patterns, habits, or conditions shaping these experiences",
    },
    5: {
        "name": "Conclusion",
        "goal": "surface insights about themselves, their identity, or their approach",
    },
    6: {
        "name": "Action Orientation",
        "goal": "consider what they'd like to try, explore, or keep noticing next",
    },
}

GUIDELINES = """Guidelines:
- Respect the user's epistemic agency: they decide what happened, what matters, and how to describe it.
- Do not label emotions, interpret motives, assign priorities, or suggest actions.
- Ask clarifying questions and invite naming, elaboration, or correction.
- Keep responses concise and take one step at a time.
- Confirm the user is ready before moving to the next Gibbs stage.
- Ground what you say in the user's own words from the journal and the conversation.
- Write in plain, warm prose. No markdown, headings, bullet points, or quotation marks around your reply.
- Address the user directly as "you"."""

_STAGE_OVERVIEW = "\n".join(
    f"{n}. {s['name']}: help the user {s['goal']}." for n, s in STAGES.items()
)


def _action_instruction(action: str, stage: dict[str, str]) -> str:
    name = stage["name"]
    goal = stage["goal"]
    if action == "open":
        return (
            f"The user is ready to begin the {name} stage. In one or two sentences, "
            f"warmly invite them to {goal}, grounded in something specific from their "
            f"journal. Ask a single open question. Do not summarise earlier stages."
        )
    if action == "clarify":
        return (
            f"Stay in the {name} stage. Ask one open clarifying question that invites "
            f"the user to elaborate on, name, or correct what they just shared. Do not "
            f"move to another stage."
        )
    if action == "reply":
        return (
            f"You are in the {name} stage. Briefly acknowledge what the user just shared "
            f"without interpreting or labelling it, then either invite them to elaborate "
            f"with one open question, or — if they seem complete — gently ask whether "
            f"they're ready to move on. One step at a time."
        )
    raise ValueError(f"Unknown action: {action}")


_ACTION_STAGE_NOTE = (
    "\n\nNote for this stage: do not pressure the user to invent a concrete action. "
    "Ground anything you raise in their own earlier words, and prefer asking what they "
    "would like to keep noticing over what they should do. Make clear it is optional."
)


def _scope_block(goal: str | None, scope_items: list[str] | None) -> str:
    """The validated scoping technique: name the focus and list the supporting excerpts
    so the facilitator stays on topic instead of drifting across the whole journal."""
    topic = (goal or "").strip()
    items = [s.strip() for s in (scope_items or []) if s and s.strip()]
    if items:
        bulleted = "\n".join(f"- {item}" for item in items)
        label = f'related to "{topic}"' if topic else "in this theme"
        return (
            f"\n\nScope: focus only on statements {label}, such as:\n{bulleted}\n"
            f"Stay within this scope; if the user drifts, gently bring them back to it."
        )
    if topic:
        return (
            f'\n\nThe user has set this focus for the whole reflection — keep your '
            f'questions oriented to it: "{topic}".'
        )
    return ""


def build_messages(
    journal_text: str,
    action: str,
    step: int | None = None,
    history: list[dict] | None = None,
    goal: str | None = None,
    scope_items: list[str] | None = None,
) -> list[dict]:
    stage = STAGES.get(step or 1, STAGES[1])

    scope_line = _scope_block(goal, scope_items)
    # The Action Orientation stage (6) is the hardest for users to answer — soften it.
    action_note = _ACTION_STAGE_NOTE if (step or 1) == 6 else ""

    system_content = f"""You are a reflective facilitator using the Gibbs reflective cycle internally to help the user reflect. Treat the journal below as a stream-of-thought journal.

The Gibbs stages, in order:
{_STAGE_OVERVIEW}

You are currently on stage {step or 1}: {stage['name']}.{scope_line}

{GUIDELINES}

Right now:
{_action_instruction(action, stage)}{action_note}"""

    messages = [{"role": "system", "content": system_content}]

    user_content = f"""Here is my journal (my included sources):

\"\"\"
{journal_text}
\"\"\""""
    messages.append({"role": "user", "content": user_content})

    # Replay the conversation so far as assistant (facilitator) / user turns.
    if history:
        for entry in history:
            question = entry.get("question")
            answer = entry.get("answer")
            if question:
                messages.append({"role": "assistant", "content": question})
            if answer:
                messages.append({"role": "user", "content": answer})

    return messages
