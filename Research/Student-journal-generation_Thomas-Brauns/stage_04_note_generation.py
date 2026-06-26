"""
Stage 04 — Note Generation
============================
Reads the repaired events from stage 03 and converts each event into
a realistic, human-like personal note. The LLM only handles surface
realization — the structure comes from the event, not the model.

Only the entities and arc relevant to each event are sent as context
(not the full world state), to keep prompts small and on-topic.

Input:  data/events_repaired.json
        data/world_state.json
Output: data/notes.json

Pipeline position:
  stage_03 → [stage_04] → stage_05

Usage:
  python stage_04_note_generation.py
"""

import json

import config
from llm import call_llm, parse_json_response
from prompts import STAGE_04_NOTE_GENERATION


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_json(label: str, key: str) -> dict:
    path = config.PATHS[key]
    if not path.exists():
        raise FileNotFoundError(
            f"{label} not found at '{path}'. Run the previous stage first."
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_notes(notes: list[dict]) -> None:
    path = config.PATHS["notes"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"notes": notes}, f, indent=2, ensure_ascii=False)
    print(f"Saved → {path}")


def _importance_label(value) -> str:
    """Convert numeric importance (1-5) to the low/medium/high label the schema expects."""
    try:
        v = int(value)
    except (ValueError, TypeError):
        return "medium"
    if v <= 2:
        return "low"
    if v == 3:
        return "medium"
    return "high"


# ── Prompt construction ───────────────────────────────────────────────────────

def build_note_prompt(event: dict, world_state: dict) -> str:
    """Inject only the entities and arc relevant to this event, not the full world state."""
    event_json = json.dumps(event, indent=2, ensure_ascii=False)

    relevant_entity_ids = set(event.get("involved_entities", []))
    relevant_entities = [
        e for e in world_state.get("entities", [])
        if e["id"] in relevant_entity_ids
    ]

    arc_id = event.get("story_arc_id")
    relevant_arcs = [
        a for a in world_state.get("story_arcs", [])
        if a["arc_id"] == arc_id
    ]

    slim_context = {"entities": relevant_entities, "story_arcs": relevant_arcs}
    context_json = json.dumps(slim_context, indent=2, ensure_ascii=False)

    return f"Context:\n{context_json}\n\nEvent:\n{event_json}\n\n{STAGE_04_NOTE_GENERATION}"


# ── Generation ────────────────────────────────────────────────────────────────

def generate_note(event: dict, world_state: dict, index: int) -> dict:
    """Generate one note from one event. Raises on parse failure (caller catches)."""
    prompt = build_note_prompt(event, world_state)
    raw    = call_llm(prompt, stage="stage_04")
    note   = parse_json_response(raw)

    if not note.get("note_id"):
        note["note_id"] = f"n_{index:04d}"
    if not note.get("timestamp"):
        note["timestamp"] = event.get("timestamp", "")
    if not note.get("story_arc_id"):
        note["story_arc_id"] = event.get("story_arc_id", "")
    if not note.get("importance"):
        note["importance"] = _importance_label(event.get("importance", 3))

    note["source_event_id"] = event.get("event_id", "")
    return note


# ── Validation ────────────────────────────────────────────────────────────────

def validate_notes(notes: list[dict]) -> list[str]:
    warnings = []
    seen_ids = set()
    required = {
        "note_id", "timestamp", "note_type", "text", "entities",
        "tags", "latent_facts", "story_arc_id", "importance",
    }

    for note in notes:
        nid = note.get("note_id", "?")

        if nid in seen_ids:
            warnings.append(f"Duplicate note_id: '{nid}'")
        seen_ids.add(nid)

        missing = required - note.keys()
        if missing:
            warnings.append(f"Note '{nid}' missing keys: {missing}")

        if not note.get("text", "").strip():
            warnings.append(f"Note '{nid}' has empty text")

        imp = note.get("importance", "")
        if imp not in ("low", "medium", "high"):
            warnings.append(f"Note '{nid}' has unexpected importance value: '{imp}'")

    return warnings


# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary(notes: list[dict], failed: int) -> None:
    if not notes:
        print("No notes generated.")
        return

    type_counts: dict[str, int] = {}
    imp_counts:  dict[str, int] = {}
    for n in notes:
        t = n.get("note_type", "unknown")
        i = n.get("importance", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
        imp_counts[i]  = imp_counts.get(i, 0) + 1

    print("\n── Note Generation Summary ──────────────────────────")
    print(f"  Notes generated : {len(notes)}")
    print(f"  Failed / skipped: {failed}")
    print(f"\n  By note type:")
    for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"    {count:3d}x  {t}")
    print(f"\n  By importance:")
    for i in ("high", "medium", "low", "unknown"):
        if i in imp_counts:
            print(f"    {imp_counts[i]:3d}x  {i}")
    sample = next((n for n in notes if n.get("text")), None)
    if sample:
        print(f"\n  Sample note:")
        print(f"    [{sample.get('note_id')}] {sample.get('timestamp', '')[:10]}")
        print(f"    \"{sample.get('text', '')[:120]}...\"")
    print("─────────────────────────────────────────────────────\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    events_data = load_json("Repaired events", "events_repaired")
    events      = events_data.get("events", [])
    world_state = load_json("World state", "world_state")

    print(f"Loaded {len(events)} repaired events. Generating notes...")

    notes  = []
    failed = 0

    for i, event in enumerate(events):
        eid = event.get("event_id", f"index {i}")
        print(f"  [{i+1:3d}/{len(events)}] {eid}...", end=" ", flush=True)

        try:
            note = generate_note(event, world_state, i)
            notes.append(note)
            print("✓")
        except Exception as exc:
            print(f"✗ ({type(exc).__name__}: {exc})")
            failed += 1

    warnings = validate_notes(notes)
    if warnings:
        print(f"\n⚠️  Validation warnings ({len(warnings)}):")
        for w in warnings:
            print(f"   - {w}")
    else:
        print("✓  Validation passed")

    save_notes(notes)
    print_summary(notes, failed)
    print("Stage 04 complete. Next: python stage_05_qa_generation.py")


if __name__ == "__main__":
    main()