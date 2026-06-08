"""
validator.py — Code-side validation replacing the LLM repair pass (Stage 3).

Checks:
  - JSON schema conformance
  - Entity cross-references (events only use declared entities)
  - Arc cross-references (events only use declared arc IDs)
  - Timestamp strict monotonicity
  - Event ID uniqueness
  - Note ID uniqueness + note→arc cross-reference
  - QA supporting_notes reference real note IDs
  - Answerability/supporting_notes consistency
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


SCHEMA_DIR = Path(__file__).parent / "schemas"


# ── helpers ──────────────────────────────────────────────────────────────────

def _load_schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / f"{name}.json").read_text())


def _schema_validate(data: Any, schema_name: str, label: str) -> list[str]:
    if not HAS_JSONSCHEMA:
        return [f"[SKIP] jsonschema not installed — skipping schema check for {label}"]
    errors = []
    validator = jsonschema.Draft7Validator(_load_schema(schema_name))
    for err in validator.iter_errors(data):
        path = " → ".join(str(p) for p in err.absolute_path) or "(root)"
        errors.append(f"  Schema error at {path}: {err.message}")
    return errors


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s)


# ── per-stage validators ──────────────────────────────────────────────────────

def validate_world_state(ws: dict) -> list[str]:
    errors = _schema_validate(ws, "world_state", "world_state")

    entity_ids = {e["entity_id"] for e in ws.get("entities", [])}
    arc_ids    = {a["arc_id"]    for a in ws.get("story_arcs", [])}

    if len(entity_ids) < 10:
        errors.append(f"  Need ≥10 entities, got {len(entity_ids)}")
    if len(arc_ids) < 3:
        errors.append(f"  Need ≥3 story arcs, got {len(arc_ids)}")

    return errors


def validate_event_stream(events_data: dict, world_state: dict) -> list[str]:
    errors = _schema_validate(events_data, "event_stream", "event_stream")

    valid_entity_ids = {e["entity_id"] for e in world_state.get("entities", [])}
    valid_entity_names = {e["name"] for e in world_state.get("entities", [])}
    valid_refs = valid_entity_ids | valid_entity_names
    valid_arc_ids = {a["arc_id"] for a in world_state.get("story_arcs", [])}

    events = events_data.get("events", [])
    seen_ids: set[str] = set()
    last_ts: datetime | None = None

    for ev in events:
        eid = ev.get("event_id", "?")

        # uniqueness
        if eid in seen_ids:
            errors.append(f"  Duplicate event_id: {eid}")
        seen_ids.add(eid)

        # timestamp monotonicity
        ts_raw = ev.get("timestamp", "")
        try:
            ts = _ts(ts_raw)
            if last_ts and ts <= last_ts:
                errors.append(
                    f"  [{eid}] timestamp not strictly increasing: {ts_raw} ≤ {last_ts.isoformat()}"
                )
            last_ts = ts
        except ValueError:
            errors.append(f"  [{eid}] invalid timestamp: {ts_raw!r}")

        # arc reference
        arc = ev.get("story_arc_id", "")
        if arc and arc not in valid_arc_ids:
            errors.append(f"  [{eid}] unknown story_arc_id: {arc!r}")

        # entity references
        for ent in ev.get("involved_entities", []):
            if ent not in valid_refs:
                errors.append(f"  [{eid}] unknown entity reference: {ent!r}")

    return errors


def validate_note_corpus(notes_data: dict, world_state: dict, events_data: dict) -> list[str]:
    errors = _schema_validate(notes_data, "note_corpus", "note_corpus")

    valid_arc_ids    = {a["arc_id"] for a in world_state.get("story_arcs", [])}
    valid_event_ids  = {e["event_id"] for e in events_data.get("events", [])}

    notes = notes_data.get("notes", [])
    seen_ids: set[str] = set()

    for note in notes:
        nid = note.get("note_id", "?")

        if nid in seen_ids:
            errors.append(f"  Duplicate note_id: {nid}")
        seen_ids.add(nid)

        arc = note.get("story_arc_id", "")
        if arc and arc not in valid_arc_ids:
            errors.append(f"  [{nid}] unknown story_arc_id: {arc!r}")

        text = note.get("text", "")
        if len(text.strip()) < 10:
            errors.append(f"  [{nid}] note text suspiciously short: {text!r}")

    return errors


def validate_qa_set(qa_data: dict, notes_data: dict) -> list[str]:
    errors = _schema_validate(qa_data, "qa_set", "qa_set")

    valid_note_ids = {n["note_id"] for n in notes_data.get("notes", [])}
    qa_pairs = qa_data.get("qa_pairs", [])

    unanswerable_count = sum(
        1 for q in qa_pairs if q.get("answerability") == "unanswerable"
    )
    if len(qa_pairs) > 5 and unanswerable_count == 0:
        errors.append("  QA set has no unanswerable questions — at least some are required")

    for q in qa_pairs:
        qid  = q.get("question_id", "?")
        ans  = q.get("answerability", "")
        snotes = q.get("supporting_notes", [])

        for nid in snotes:
            if nid not in valid_note_ids:
                errors.append(f"  [{qid}] supporting note {nid!r} not in note corpus")

        if ans == "answerable" and not snotes:
            errors.append(f"  [{qid}] marked answerable but has no supporting_notes")

        if ans == "unanswerable" and snotes:
            errors.append(
                f"  [{qid}] marked unanswerable but lists supporting notes: {snotes}"
            )

    return errors


# ── top-level entry point ─────────────────────────────────────────────────────

def run_all(
    world_state:  dict,
    events_data:  dict,
    notes_data:   dict,
    qa_data:      dict,
) -> dict[str, list[str]]:
    """
    Run all four validators. Returns a dict of stage → [error strings].
    Empty list means the stage passed.
    """
    return {
        "world_state":   validate_world_state(world_state),
        "event_stream":  validate_event_stream(events_data, world_state),
        "note_corpus":   validate_note_corpus(notes_data, world_state, events_data),
        "qa_set":        validate_qa_set(qa_data, notes_data),
    }


def print_report(results: dict[str, list[str]]) -> bool:
    """Print a human-readable report. Returns True if all stages passed."""
    all_ok = True
    for stage, errors in results.items():
        if errors:
            all_ok = False
            print(f"\n❌  {stage.upper()} — {len(errors)} issue(s):")
            for e in errors:
                print(e)
        else:
            print(f"✅  {stage.upper()} — OK")
    return all_ok
