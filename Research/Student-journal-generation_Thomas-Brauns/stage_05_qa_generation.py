"""
Stage 05 — QA Generation
==========================
Reads notes.json and generates question-answer pairs grounded in the
note corpus. Uses evidence-first generation: the supporting notes are
chosen before the question is written, so gold evidence is always correct.

Five QA types with increasing difficulty:
  single_hop          — one note is sufficient
  multi_hop           — two or more notes required
  temporal_reasoning  — answer depends on event ordering
  conflict_resolution — two notes contradict each other
  unanswerable        — answer is not present in the notes

Input:  data/notes.json
Output: data/qa_pairs.json

Pipeline position:
  stage_04 → [stage_05]

Usage:
  python stage_05_qa_generation.py
"""

import json
import random
from collections import Counter, defaultdict
from enum import Enum

import config
from llm import call_llm, parse_json_response
from prompts import STAGE_05_QA


class QAType(Enum):
    SINGLE_HOP   = "single_hop"
    MULTI_HOP    = "multi_hop"
    TEMPORAL     = "temporal_reasoning"
    CONFLICT     = "conflict_resolution"
    UNANSWERABLE = "unanswerable"


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_json(label: str, key: str) -> dict:
    path = config.PATHS[key]
    if not path.exists():
        raise FileNotFoundError(
            f"{label} not found at '{path}'. Run the previous stage first."
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_qa_pairs(qa_pairs: list[dict]) -> None:
    path = config.PATHS["qa_pairs"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"qa_pairs": qa_pairs}, f, indent=2, ensure_ascii=False)
    print(f"Saved → {path}")


def _entity_key(entity) -> str:
    """Notes may store entities as plain ID strings or as dicts with an 'id' field."""
    return entity.get("id") if isinstance(entity, dict) else str(entity)


# ── Evidence finders ───────────────────────────────────────────────────────────
# Each finder returns a list of note-ID groups. The group defines the gold
# evidence for one QA pair — chosen BEFORE the question is written.

def find_single_hop_seeds(notes: list[dict]) -> list[list[str]]:
    """One note with a clear, answerable fact."""
    return [
        [n["note_id"]]
        for n in notes
        if n.get("text", "").strip() and n.get("importance") in ("medium", "high")
    ]


def find_multi_hop_seeds(notes: list[dict]) -> list[list[str]]:
    """
    Note pairs that share an entity but are not adjacent in time —
    the answer requires combining both.
    """
    by_entity: dict[str, list[dict]] = defaultdict(list)
    for note in sorted(notes, key=lambda n: n.get("timestamp", "")):
        for entity in note.get("entities", []):
            by_entity[_entity_key(entity)].append(note)

    pairs = []
    for entity_notes in by_entity.values():
        for i in range(len(entity_notes) - 2):
            pairs.append([entity_notes[i]["note_id"], entity_notes[i + 2]["note_id"]])
    return pairs


def find_temporal_seeds(notes: list[dict]) -> list[list[str]]:
    """Three consecutive notes for the same arc — requires reconstructing the timeline."""
    by_arc: dict[str, list[dict]] = defaultdict(list)
    for note in sorted(notes, key=lambda n: n.get("timestamp", "")):
        arc = note.get("story_arc_id")
        if arc:
            by_arc[arc].append(note)

    return [
        [n["note_id"] for n in arc_notes[:3]]
        for arc_notes in by_arc.values()
        if len(arc_notes) >= 3
    ]


def find_conflict_seeds(notes: list[dict]) -> list[list[str]]:
    """Notes that share an entity and have differing latent_fact values."""
    entity_facts: dict[tuple, dict] = {}
    pairs = []

    for note in sorted(notes, key=lambda n: n.get("timestamp", "")):
        for entity in note.get("entities", []):
            entity_key = _entity_key(entity)
            for fact in note.get("latent_facts", []):
                key = (entity_key, str(fact)[:40])
                if key in entity_facts:
                    prev = entity_facts[key]
                    if prev["note_id"] != note["note_id"]:
                        pairs.append([prev["note_id"], note["note_id"]])
                else:
                    entity_facts[key] = {"note_id": note["note_id"]}
    return pairs


def find_unanswerable_seeds(notes: list[dict]) -> list[list[str]]:
    """Notes that hint at something without resolving it."""
    hedge_words = ("think", "maybe", "not sure", "might", "forgot", "can't remember")
    return [
        [n["note_id"]]
        for n in notes
        if any(word in n.get("text", "").lower() for word in hedge_words)
    ]


SEED_FINDERS = {
    QAType.SINGLE_HOP:   find_single_hop_seeds,
    QAType.MULTI_HOP:    find_multi_hop_seeds,
    QAType.TEMPORAL:     find_temporal_seeds,
    QAType.CONFLICT:     find_conflict_seeds,
    QAType.UNANSWERABLE: find_unanswerable_seeds,
}


# ── Generation ────────────────────────────────────────────────────────────────

def generate_qa_pair(
    note_ids: list[str],
    notes_by_id: dict[str, dict],
    qa_type: QAType,
    index: int,
) -> dict | None:
    notes_text = "\n\n".join(
        f"[{nid}] {notes_by_id[nid]['text']}"
        for nid in note_ids
        if nid in notes_by_id
    )
    if not notes_text.strip():
        return None

    prompt = STAGE_05_QA.format(
        qa_type=qa_type.value,
        notes_text=notes_text,
        note_ids=json.dumps(note_ids),
        hop_count=len(note_ids),
    )

    raw = call_llm(prompt, stage="stage_05")
    qa  = parse_json_response(raw)

    qa["question_id"]      = f"q_{index:04d}"
    qa["supporting_notes"] = note_ids  # always override with ground truth
    qa["required_hops"]    = len(note_ids)
    return qa


# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary(qa_pairs: list[dict], failed: int) -> None:
    types = Counter(q.get("reasoning_type") for q in qa_pairs)
    diffs = Counter(q.get("difficulty") for q in qa_pairs)
    hops  = Counter(q.get("required_hops") for q in qa_pairs)

    print("\n── QA Generation Summary ────────────────────────────")
    print(f"  Generated : {len(qa_pairs)}   Failed: {failed}")
    print(f"\n  By type:")
    for t, c in sorted(types.items()):
        print(f"    {c:3d}x  {t}")
    print(f"\n  By difficulty:")
    for d in ("easy", "medium", "hard"):
        print(f"    {diffs.get(d, 0):3d}x  {d}")
    print(f"\n  By required hops:")
    for h, c in sorted(hops.items()):
        print(f"    {c:3d}x  {h} hop(s)")
    print("─────────────────────────────────────────────────────\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    notes_data  = load_json("Notes", "notes")
    notes       = notes_data.get("notes", [])
    notes_by_id = {n["note_id"]: n for n in notes}

    print(f"Loaded {len(notes)} notes.")

    qa_pairs = []
    failed   = 0
    index    = 0

    for qa_type, finder in SEED_FINDERS.items():
        seeds  = finder(notes)
        count  = config.QA_COUNT.get(qa_type.value, 3)
        sample = random.sample(seeds, min(count, len(seeds)))

        print(f"\n  [{qa_type.value}] {len(seeds)} seeds found, generating {len(sample)}...")

        for note_ids in sample:
            print(f"    [{index+1:3d}] {note_ids}...", end=" ", flush=True)
            try:
                qa = generate_qa_pair(note_ids, notes_by_id, qa_type, index)
                if qa:
                    qa_pairs.append(qa)
                    print("✓")
                else:
                    print("✗ (empty)")
                    failed += 1
            except Exception as exc:
                print(f"✗ ({type(exc).__name__}: {exc})")
                failed += 1
            index += 1

    save_qa_pairs(qa_pairs)
    print_summary(qa_pairs, failed)
    print("Stage 05 complete. Pipeline finished.")


if __name__ == "__main__":
    main()