"""
Stage 02 — Event Timeline Generator
=====================================
Reads the world state from stage 01 and generates a chronological
timeline of events that advance the story arcs and update latent facts.

Event skeletons (entity, arc, timestamp) are pre-filled by the knowledge
graph via a biased random walk. The LLM only writes the text and
latent_fact_updates fields. Contradiction skeletons are injected for
every unresolved arc to ensure conflict_resolution QA pairs are possible.

Input:  data/world_state.json
Output: data/events_raw.json

Pipeline position:
  stage_01 → [stage_02] → stage_03 → stage_04 → stage_05

Usage:
  python stage_02_event_timeline.py
"""

import json
import random
from datetime import datetime, timedelta

import config
from llm import call_llm, parse_json_response
from prompts import STAGE_02_EVENT_TIMELINE


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_world_state() -> dict:
    path = config.PATHS["world_state"]
    if not path.exists():
        raise FileNotFoundError(
            f"World state not found at '{path}'. Run stage_01_world_state.py first."
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_events(events_data: dict) -> None:
    path = config.PATHS["events_raw"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(events_data, f, indent=2, ensure_ascii=False)
    print(f"Saved → {path}")


# ── Skeleton generation ───────────────────────────────────────────────────────

def build_skeletons(world_state: dict) -> list[dict]:
    """
    Build event skeletons via a biased random walk over the knowledge graph,
    then inject contradiction skeletons for each unresolved arc.
    """
    from knowledge_graph import load_graph, build_timeline_skeletons, GraphValidator

    G = load_graph(world_state)

    start_date = datetime.fromisoformat(config.START_DATE).replace(hour=9)
    skeletons = build_timeline_skeletons(
        G,
        start_date=start_date,
        duration_days=config.DURATION_DAYS,
        events_per_day=config.EVENTS_PER_DAY,
    )
    print(f"  {len(skeletons)} skeletons generated via biased random walk.")

    skeletons = _inject_contradictions(skeletons, G, GraphValidator(G))
    print(f"  {len(skeletons)} skeletons after contradiction injection.")

    return skeletons


def _inject_contradictions(skeletons: list[dict], G, validator) -> list[dict]:
    """
    For every active or stalled arc, inject a contradiction skeleton later
    in the timeline. The LLM is instructed to revise or contradict a fact
    from the first event in that arc.
    """
    contradiction_skeletons = []

    for arc_id in validator.unresolved_arcs():
        arc_skeletons = [s for s in skeletons if s.get("story_arc_id") == arc_id]
        if not arc_skeletons:
            continue

        first = arc_skeletons[0]
        base_ts = datetime.fromisoformat(first["timestamp"])
        later_ts = base_ts + timedelta(days=random.randint(5, 14))

        contradiction_skeletons.append({
            "event_id":            f"E_contra_{arc_id}",
            "timestamp":           later_ts.isoformat(),
            "primary_entity":      first["primary_entity"],
            "story_arc_id":        arc_id,
            "involved_entities":   first["involved_entities"],
            "text":                None,
            "latent_fact_updates": [],
            "importance":          None,
            "_contradiction_of":   first["event_id"],
            "_instruction": (
                "This event must contradict or revise a fact established in the "
                "earlier event it references. Same entities, different outcome or status."
            ),
        })

    all_skeletons = skeletons + contradiction_skeletons
    all_skeletons.sort(key=lambda s: s["timestamp"])
    return all_skeletons


# ── Generation ────────────────────────────────────────────────────────────────

def generate_events(world_state: dict, skeletons: list[dict]) -> dict:
    """Send world state and skeletons to the LLM; return parsed events dict."""
    print(f"Generating event text via {config.BACKEND} ({config.OLLAMA_MODEL})...")
    world_state_json = json.dumps(world_state, indent=2, ensure_ascii=False)
    skeletons_json   = json.dumps(skeletons, indent=2, ensure_ascii=False)

    prompt = (
        f"World state:\n{world_state_json}\n\n"
        f"Event skeletons:\n{skeletons_json}\n\n"
        f"{STAGE_02_EVENT_TIMELINE}"
    )
    raw = call_llm(prompt, stage="stage_02")
    return parse_json_response(raw)


# ── Validation ────────────────────────────────────────────────────────────────

def validate_events(events_data: dict, world_state: dict) -> list[str]:
    warnings = []
    events = events_data.get("events", [])

    if not events:
        warnings.append("No events generated.")
        return warnings

    if len(events) < 10:
        warnings.append(f"Only {len(events)} events — expected ≥10")

    valid_entity_ids = {e.get("id") for e in world_state.get("entities", [])}
    valid_arc_ids    = {a.get("arc_id") for a in world_state.get("story_arcs", [])}
    required_keys    = {
        "event_id", "timestamp", "event_type", "involved_entities",
        "story_arc_id", "latent_fact_updates", "importance",
    }
    seen_ids   = set()
    prev_ts    = ""

    for i, event in enumerate(events):
        eid = event.get("event_id", f"[index {i}]")

        if eid in seen_ids:
            warnings.append(f"Duplicate event_id: '{eid}'")
        seen_ids.add(eid)

        missing = required_keys - event.keys()
        if missing:
            warnings.append(f"Event '{eid}' missing keys: {missing}")

        ts = event.get("timestamp", "")
        if ts and prev_ts and ts < prev_ts:
            warnings.append(f"Event '{eid}' timestamp out of order: {ts} after {prev_ts}")
        if ts:
            prev_ts = ts

        for entity in event.get("involved_entities", []):
            if entity not in valid_entity_ids:
                warnings.append(f"Event '{eid}' references unknown entity: '{entity}'")

        arc = event.get("story_arc_id")
        if arc and arc not in valid_arc_ids:
            warnings.append(f"Event '{eid}' references unknown arc: '{arc}'")

        importance = event.get("importance")
        if importance is not None:
            try:
                if not (1 <= int(importance) <= 5):
                    warnings.append(f"Event '{eid}' importance out of range: {importance}")
            except (ValueError, TypeError):
                warnings.append(f"Event '{eid}' importance is not a number: '{importance}'")

    return warnings


# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary(events_data: dict) -> None:
    events = events_data.get("events", [])
    if not events:
        print("No events to summarise.")
        return

    type_counts: dict[str, int] = {}
    arc_counts:  dict[str, int] = {}
    for e in events:
        t = e.get("event_type", "unknown")
        a = e.get("story_arc_id", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
        arc_counts[a]  = arc_counts.get(a, 0) + 1

    first_ts = events[0].get("timestamp", "?")
    last_ts  = events[-1].get("timestamp", "?")

    print("\n── Event Timeline Summary ───────────────────────────")
    print(f"  Total events : {len(events)}")
    print(f"  Date range   : {first_ts[:10]} → {last_ts[:10]}")
    print(f"\n  By event type:")
    for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"    {count:3d}x  {t}")
    print(f"\n  By story arc:")
    for a, count in sorted(arc_counts.items(), key=lambda x: -x[1]):
        print(f"    {count:3d}x  {a}")
    print("─────────────────────────────────────────────────────\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    world_state = load_world_state()
    print(
        f"Loaded world state: {world_state['user_profile'].get('name')}, "
        f"{len(world_state.get('entities', []))} entities, "
        f"{len(world_state.get('story_arcs', []))} arcs"
    )

    print("Building event skeletons via knowledge graph...")
    skeletons = build_skeletons(world_state)

    events_data = generate_events(world_state, skeletons)

    warnings = validate_events(events_data, world_state)
    if warnings:
        print(f"\n⚠️  Validation warnings ({len(warnings)}):")
        for w in warnings:
            print(f"   - {w}")
    else:
        print("✓  Validation passed")

    save_events(events_data)
    print_summary(events_data)
    print("Stage 02 complete. Next: python stage_03_repair.py")


if __name__ == "__main__":
    main()