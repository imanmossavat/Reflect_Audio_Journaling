"""
pipeline.py — Lean 4-stage synthetic RAG dataset pipeline.

Stages:
  1. World state generation     → outputs/world_state.json
  2. Event stream generation    → outputs/event_stream.json
     [code-side validation]     (replaces LLM repair pass)
  3. Note corpus generation     → outputs/note_corpus.json
  4. QA set generation          → outputs/qa_set.json

Usage:
  python pipeline.py                        # run all stages
  python pipeline.py --stage 1              # run only stage 1
  python pipeline.py --from-stage 3        # resume from stage 3
  python pipeline.py --validate-only       # validate existing outputs

Requirements:
  pip install anthropic jsonschema
  export ANTHROPIC_API_KEY=sk-...
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import anthropic

import prompts
import validator

# ── Config ────────────────────────────────────────────────────────────────────

MODEL         = "claude-opus-4-6"
MAX_TOKENS    = 8192
OUTPUT_DIR    = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

PATHS = {
    "world_state":  OUTPUT_DIR / "world_state.json",
    "event_stream": OUTPUT_DIR / "event_stream.json",
    "note_corpus":  OUTPUT_DIR / "note_corpus.json",
    "qa_set":       OUTPUT_DIR / "qa_set.json",
}

# ── Claude client ─────────────────────────────────────────────────────────────

def get_client() -> anthropic.Anthropic:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        sys.exit("❌  ANTHROPIC_API_KEY not set. Export it and retry.")
    return anthropic.Anthropic(api_key=key)


# ── Core LLM call ─────────────────────────────────────────────────────────────

def call_claude(client: anthropic.Anthropic, system: str, user: str, label: str) -> dict:
    """
    Call Claude and return parsed JSON. Retries once on JSON parse failure.
    """
    print(f"\n  → Calling Claude for {label}…", flush=True)

    for attempt in range(1, 3):
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        raw = response.content[0].text.strip()

        # strip accidental markdown fences
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$",         "", raw)

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            print(f"  ⚠️  JSON parse failed (attempt {attempt}): {exc}")
            if attempt == 2:
                debug_path = OUTPUT_DIR / f"{label}_raw_attempt{attempt}.txt"
                debug_path.write_text(raw)
                sys.exit(
                    f"❌  Could not parse JSON from Claude after 2 attempts.\n"
                    f"    Raw output saved to {debug_path}"
                )

    # unreachable
    raise RuntimeError("Unexpected exit from call_claude retry loop")


# ── Save / load helpers ───────────────────────────────────────────────────────

def save(data: dict, key: str) -> None:
    path = PATHS[key]
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"  ✅  Saved → {path}")


def load(key: str) -> dict:
    path = PATHS[key]
    if not path.exists():
        sys.exit(f"❌  Required file not found: {path}\n    Run earlier stages first.")
    return json.loads(path.read_text())


def validate_and_abort_on_errors(results: dict[str, list[str]]) -> None:
    """Print validation report. Abort if any stage has errors."""
    all_ok = validator.print_report(results)
    if not all_ok:
        sys.exit(
            "\n❌  Validation failed. Fix the issues above and re-run, "
            "or edit the output files manually, then re-run with --from-stage <next>."
        )


# ── Stages ────────────────────────────────────────────────────────────────────

def stage1_world_state(client: anthropic.Anthropic) -> dict:
    print("\n── Stage 1: World State Generation ─────────────────────────────────")
    data = call_claude(client, prompts.STAGE1_SYSTEM, prompts.STAGE1_USER, "world_state")
    errors = validator.validate_world_state(data)
    if errors:
        print("  ⚠️  Validation issues:")
        for e in errors:
            print(e)
        print("  Continuing — fix outputs/world_state.json manually if needed.")
    save(data, "world_state")
    return data


def stage2_event_stream(client: anthropic.Anthropic, world_state: dict) -> dict:
    print("\n── Stage 2: Event Stream Generation ────────────────────────────────")
    ws_json = json.dumps(world_state, indent=2)
    data = call_claude(
        client,
        prompts.STAGE2_SYSTEM,
        prompts.STAGE2_USER.format(world_state_json=ws_json),
        "event_stream",
    )

    print("\n  Running code-side validation (replaces LLM repair pass)…")
    errors = validator.validate_event_stream(data, world_state)
    if errors:
        print("  ⚠️  Event stream validation issues:")
        for e in errors:
            print(e)
        print(
            "\n  These will NOT auto-repair. Edit outputs/event_stream.json\n"
            "  and re-run with --from-stage 3, or accept minor inconsistencies."
        )
    else:
        print("  ✅  Event stream valid")

    save(data, "event_stream")
    return data


def stage3_note_corpus(client: anthropic.Anthropic, world_state: dict, event_stream: dict) -> dict:
    print("\n── Stage 3: Note Corpus Generation ─────────────────────────────────")
    events_json = json.dumps(event_stream, indent=2)
    data = call_claude(
        client,
        prompts.STAGE4_SYSTEM,
        prompts.STAGE4_USER.format(events_json=events_json),
        "note_corpus",
    )

    errors = validator.validate_note_corpus(data, world_state, event_stream)
    if errors:
        print("  ⚠️  Note corpus validation issues:")
        for e in errors:
            print(e)
    else:
        print("  ✅  Note corpus valid")

    save(data, "note_corpus")
    return data


def stage4_qa_set(client: anthropic.Anthropic, note_corpus: dict) -> dict:
    print("\n── Stage 4: QA Set Generation ───────────────────────────────────────")
    notes_json = json.dumps(note_corpus, indent=2)
    data = call_claude(
        client,
        prompts.STAGE5_SYSTEM,
        prompts.STAGE5_USER.format(notes_json=notes_json),
        "qa_set",
    )

    errors = validator.validate_qa_set(data, note_corpus)
    if errors:
        print("  ⚠️  QA set validation issues:")
        for e in errors:
            print(e)
    else:
        print("  ✅  QA set valid")

    save(data, "qa_set")
    return data


# ── Validate-only mode ────────────────────────────────────────────────────────

def validate_only() -> None:
    print("\n── Validating existing outputs ──────────────────────────────────────")
    ws  = load("world_state")
    es  = load("event_stream")
    nc  = load("note_corpus")
    qa  = load("qa_set")
    results = validator.run_all(ws, es, nc, qa)
    validator.print_report(results)


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Synthetic RAG Memory Dataset Pipeline")
    group = p.add_mutually_exclusive_group()
    group.add_argument(
        "--stage", type=int, choices=[1, 2, 3, 4],
        help="Run only this stage (loads prior outputs from disk)",
    )
    group.add_argument(
        "--from-stage", type=int, choices=[1, 2, 3, 4],
        dest="from_stage",
        help="Resume pipeline from this stage onwards",
    )
    group.add_argument(
        "--validate-only", action="store_true",
        help="Validate existing output files without generating anything",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if args.validate_only:
        validate_only()
        return

    client = get_client()

    # Determine which stages to run
    if args.stage:
        run = {args.stage}
    elif args.from_stage:
        run = set(range(args.from_stage, 5))
    else:
        run = {1, 2, 3, 4}

    print(f"Running stages: {sorted(run)}")

    # Stage 1
    if 1 in run:
        world_state = stage1_world_state(client)
    else:
        world_state = load("world_state")

    # Stage 2
    if 2 in run:
        event_stream = stage2_event_stream(client, world_state)
    else:
        event_stream = load("event_stream")

    # Stage 3
    if 3 in run:
        note_corpus = stage3_note_corpus(client, world_state, event_stream)
    else:
        note_corpus = load("note_corpus")

    # Stage 4
    if 4 in run:
        stage4_qa_set(client, note_corpus)

    print("\n\n── Pipeline complete ─────────────────────────────────────────────────")
    print(f"  Outputs in: {OUTPUT_DIR.resolve()}")
    for key, path in PATHS.items():
        size = f"{path.stat().st_size / 1024:.1f} KB" if path.exists() else "missing"
        print(f"  {key:<16} {path.name}  ({size})")


if __name__ == "__main__":
    main()
