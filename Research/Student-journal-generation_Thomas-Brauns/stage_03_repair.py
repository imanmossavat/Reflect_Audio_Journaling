"""
Stage 03 — Repair Pass
========================
Reads the raw events from stage 02 and fixes structural issues
deterministically using the knowledge graph. No LLM is used.

The key principle is minimal-edit: only fix what is provably wrong
using the world state as ground truth. Messiness in event text is
intentional and must be preserved.

Fixes applied:
  - Unknown entity IDs stripped from involved_entities
  - Invalid story_arc_id values nulled
  - Importance values clamped to 1–5
  - Timestamps re-sorted to ensure strict chronological order

Input:  data/world_state.json
        data/events_raw.json
Output: data/events_repaired.json

Pipeline position:
  stage_02 → [stage_03] → stage_04 → stage_05

Usage:
  python stage_03_repair.py
"""

import json

import config


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_json(label: str, key: str) -> dict:
    path = config.PATHS[key]
    if not path.exists():
        raise FileNotFoundError(
            f"{label} not found at '{path}'. Run the previous stage first."
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_events(events: list[dict]) -> None:
    path = config.PATHS["events_repaired"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"events": events}, f, indent=2, ensure_ascii=False)
    print(f"Saved → {path}")


# ── Repair ────────────────────────────────────────────────────────────────────

def repair_and_validate(events: list[dict], world_state: dict) -> tuple[list[dict], list[str]]:
    """
    Apply graph-based deterministic repair to the raw event list.

    Returns:
        (repaired_events, repair_log)
    """
    from knowledge_graph import load_graph, GraphValidator

    G         = load_graph(world_state)
    validator = GraphValidator(G)
    repaired  = []
    log       = []

    for event in events:
        fixed, entry = validator.repair_event(event)
        repaired.append(fixed)
        log.extend(entry)

    # Re-sort by timestamp after repair (out-of-order events are fixed here,
    # not by the LLM, keeping the process deterministic).
    repaired.sort(key=lambda e: e.get("timestamp", ""))

    return repaired, log


# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary(log: list[str], count_before: int, count_after: int) -> None:
    print("\n── Repair Summary ───────────────────────────────────")
    print(f"  Events before    : {count_before}")
    print(f"  Events after     : {count_after}")
    print(f"  Fixes applied    : {len(log)}")
    for entry in log[:10]:
        print(f"    · {entry}")
    if len(log) > 10:
        print(f"    ... and {len(log) - 10} more")
    print("─────────────────────────────────────────────────────\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    from knowledge_graph import load_graph, GraphValidator

    world_state = load_json("World state", "world_state")
    events_data = load_json("Raw events", "events_raw")
    raw_events  = events_data.get("events", [])

    print(f"Loaded {len(raw_events)} raw events. Running graph-based repair...")

    repaired, log = repair_and_validate(raw_events, world_state)

    # Post-repair validation
    G         = load_graph(world_state)
    validator = GraphValidator(G)
    warnings  = validator.validate_timeline(repaired)

    if warnings:
        print(f"\n⚠️  Remaining issues after repair ({len(warnings)}):")
        for w in warnings:
            print(f"   - {w}")
    else:
        print("✓  Validation passed — no issues remaining")

    save_events(repaired)
    print_summary(log, len(raw_events), len(repaired))
    print("Stage 03 complete. Next: python stage_04_note_generation.py")


if __name__ == "__main__":
    main()