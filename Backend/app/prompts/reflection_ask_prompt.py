"""Ask prompt assembly — Document B §5.

Slot order matters (models attend more reliably to the start/end of a prompt
than the middle): role/policy, focus, gist, open thread, retrieved source
units, student message, response rules. The model never sees a stage name,
a step number, or the conversation history — only these slots.
"""

ROLE_POLICY = """You are a reflective facilitator helping a student think through a personal
journal entry. You are a support for their own thinking, not the one doing
the thinking. Respect their epistemic agency: they decide what happened,
what matters, and how to describe it. Ground what you say in the source
material you are given, not in a running tally of what has already been
said. Write in plain, warm prose. No markdown, headings, bullet points, or
quotation marks around your reply. Address the student directly as "you"."""

RESPONSE_RULES = """Normal turn:
- Ask exactly one focused question.
- Use the student's own words when referencing what they said.
- Never label an emotion, motive, or interpretation the student did not
  state. This is a hard constraint, not situational.
- If you reference something the student wrote, cite it inline as
  {{source_id:unit_id}}.
- Maximum 120 words.

If this is the opening turn (no conversation yet):
  Open with one question grounded in the retrieved source units most
  relevant to the student's chosen focus. Do not ask the student to
  restate what's already in the sources.

If the student's message is very short or unclear:
  Do not guess at meaning. Ask one open question to invite more.
  e.g. "Can you tell me a bit more about that?"

If the student seems to be going off-topic:
  Acknowledge briefly in one clause, then return to the open thread.
  e.g. "That's worth noting — coming back to [open thread]..."

If the student expresses resistance or says they don't know:
  Do not push. Offer a simpler, more concrete version of the question.
  e.g. "That's okay — what's one thing you remember clearly about that?"

Never repeat a question that has already been asked and answered, even
briefly. If a question didn't land, try a different angle next turn.

If in doubt: ask the simplest possible question and wait."""


def _units_block(units: list) -> str:
    if not units:
        return "(no retrieved source material this turn)"
    return "\n".join(f"[{u.source_id}:{u.unit_id}] {u.text}" for u in units)


def build_ask_messages(
    focus_value: str,
    gist_text: str,
    open_thread_text: str | None,
    retrieved_units: list,
    student_message: str | None,
    *,
    is_session_start: bool,
) -> list[dict]:
    """Assemble the Ask (generation) prompt per Document B §5."""
    gist_block = gist_text.strip() if gist_text and gist_text.strip() else "No conversation yet."
    open_thread_block = (
        open_thread_text.strip()
        if open_thread_text and open_thread_text.strip()
        else "None yet — this is the opening turn."
    )

    system_content = f"""{ROLE_POLICY}

Current focus: {focus_value}

Where the conversation currently stands (Gist):
{gist_block}

Open thread:
{open_thread_block}

Retrieved source material for this turn:
{_units_block(retrieved_units)}

{RESPONSE_RULES}"""

    messages = [{"role": "system", "content": system_content}]
    if student_message and not is_session_start:
        messages.append({"role": "user", "content": student_message})
    elif not is_session_start:
        # student_message may be empty on a clarify/continue turn with no new text
        messages.append({"role": "user", "content": "(no new message — continue per the rules above)"})
    return messages
