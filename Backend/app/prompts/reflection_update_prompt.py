"""Update (extraction) prompt assembly — Document B §6.

Produces strict JSON: a regenerated Gist, the next Open Thread, and an
optional focus-shift suggestion. Never sees a stage name or a fact ledger —
only the prior Gist/Open Thread (as light orientation, not something to
incrementally edit), the exchange that just happened, and the source units
Ask was given.
"""

INSTRUCTION = """Regenerate the Gist and Open Thread from the material below.

Gist rules (this is the important part — drift mitigation):
- Every sentence in the new Gist must carry at least one citation pointing
  to a source unit, or be directly attributable to something the student
  said in the current exchange — not to your own prior synthesis of it.
- A sentence carried forward from the previous Gist that no longer has a
  traceable citation must be dropped, not silently kept.
- Regenerate primarily from the source units and the current exchange; use
  the previous Gist only as light orientation for what's already been
  covered.
- Your citations are independent of whatever inline {{source_id:unit_id}}
  tokens appeared in the facilitator's reply — ground your own, don't just
  copy them.

Open Thread rules:
- If settled is true, the next Open Thread must be grounded in a source
  unit or in something new the student just said — never invented from
  your own sense that "this would be a good next question."
- Replace, don't append. There is never more than one Open Thread.
- There is no numeric or keyword threshold for "settled" — use your own
  judgment about whether this line of inquiry has actually been explored.

Focus rules:
- focus_shift_suggested is a suggestion the interface may show the
  student. It never changes the focus directly — leave it null unless the
  exchange clearly suggests a different focus would serve the student
  better.

Output strict JSON only — no markdown fences, no preamble, no trailing
text. Exactly this shape:
{
  "gist": {"text": "string", "citations": [{"source_id": "string", "unit_id": "string"}]},
  "open_thread": {"settled": false, "next": "string or null", "source_ref": {"source_id": "string", "unit_id": "string"} or null},
  "focus_shift_suggested": "string or null"
}"""


def _units_block(units: list) -> str:
    if not units:
        return "(no source material was retrieved this turn)"
    return "\n".join(f"[{u.source_id}:{u.unit_id}] {u.text}" for u in units)


def build_update_messages(
    prior_gist_text: str,
    prior_open_thread_text: str | None,
    student_message: str,
    facilitator_reply: str,
    retrieved_units: list,
) -> list[dict]:
    """Assemble the Update (extraction) prompt per Document B §6."""
    prior_gist_block = prior_gist_text.strip() if prior_gist_text and prior_gist_text.strip() else "(none yet)"
    prior_open_thread_block = (
        prior_open_thread_text.strip()
        if prior_open_thread_text and prior_open_thread_text.strip()
        else "(none yet)"
    )

    system_content = f"""Prior Gist (light orientation only):
{prior_gist_block}

Prior Open Thread (light orientation only):
{prior_open_thread_block}

The exchange that just happened:
Student: {student_message}
Facilitator: {facilitator_reply}

Source units the facilitator was given this turn:
{_units_block(retrieved_units)}

{INSTRUCTION}"""

    return [{"role": "system", "content": system_content}]
