"""
Stage 01 — World State Generator
==================================
Generates the hidden canonical truth for one synthetic user.
This is the foundation of the entire pipeline — all later stages
(events, notes, QA) must stay consistent with this world state.

Output: data/world_state.json

Pipeline position:
  [stage_01] → stage_02 → stage_03 → stage_04 → stage_05

Usage:
  python stage_01_world_state.py
"""

import json

import config
from llm import call_llm, parse_json_response
from prompts import STAGE_01_WORLD_STATE


# ── Generation ────────────────────────────────────────────────────────────────

def generate_world_state() -> dict:
    """Call the LLM and return the parsed world state dict."""
    print(f"Generating world state via {config.BACKEND} ({config.OLLAMA_MODEL})...")
    raw = call_llm(STAGE_01_WORLD_STATE, stage="stage_01")
    return parse_json_response(raw)


# ── Validation ────────────────────────────────────────────────────────────────

def validate_world_state(world_state: dict) -> list[str]:
    """
    Structural validation against the expected schema.
    Returns a list of warning strings (empty = all good).
    """
    warnings = []
    required_keys = {"user_profile", "entities", "story_arcs", "projects", "latent_facts"}

    for key in required_keys:
        if key not in world_state:
            warnings.append(f"Missing top-level key: '{key}'")

    entities = world_state.get("entities", [])
    if len(entities) < config.MIN_ENTITIES:
        warnings.append(
            f"Only {len(entities)} entities — minimum is {config.MIN_ENTITIES}"
        )

    entity_ids = {e.get("id") for e in entities}
    for arc in world_state.get("story_arcs", []):
        for eid in arc.get("involved_entities", []):
            if eid not in entity_ids:
                warnings.append(
                    f"Arc '{arc.get('arc_id')}' references unknown entity '{eid}'"
                )

    return warnings


# ── Persistence ───────────────────────────────────────────────────────────────

def save_world_state(world_state: dict) -> None:
    path = config.PATHS["world_state"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(world_state, f, indent=2, ensure_ascii=False)
    print(f"Saved → {path}")


# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary(world_state: dict) -> None:
    profile = world_state.get("user_profile", {})
    print("\n── World State Summary ──────────────────────────────")
    print(f"  User        : {profile.get('name')} (age {profile.get('age')})")
    print(f"  Occupation  : {profile.get('occupation')}")
    print(f"  Location    : {profile.get('location')}")
    print(f"  Entities    : {len(world_state.get('entities', []))}")
    print(f"  Story arcs  : {len(world_state.get('story_arcs', []))}")
    print(f"  Projects    : {len(world_state.get('projects', []))}")
    print(f"  Latent facts: {len(world_state.get('latent_facts', []))}")
    print("\n  Arcs:")
    for arc in world_state.get("story_arcs", []):
        print(f"    [{arc.get('status', '?'):10s}] {arc.get('arc_id')} — {arc.get('title')}")
    print("─────────────────────────────────────────────────────\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    world_state = generate_world_state()

    warnings = validate_world_state(world_state)
    if warnings:
        print(f"\n⚠️  Validation warnings ({len(warnings)}):")
        for w in warnings:
            print(f"   - {w}")
    else:
        print("✓  Validation passed")

    save_world_state(world_state)
    print_summary(world_state)
    print("Stage 01 complete. Next: python stage_02_event_timeline.py")


if __name__ == "__main__":
    main()