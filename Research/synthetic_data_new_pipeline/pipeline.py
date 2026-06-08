"""
pipeline.py — Lean 4-stage synthetic RAG dataset pipeline.

Stages:
  1. World state generation     → outputs/world_state.json
  2. Event stream generation    → outputs/event_stream.json
     [code-side validation]     (replaces LLM repair pass)
  3. Note corpus generation     → outputs/note_corpus.json
  4. QA set generation          → outputs/qa_set.json

Usage:
  python pipeline.py                             # Anthropic API, all stages
  python pipeline.py --backend ollama            # local Ollama, all stages
  python pipeline.py --backend ollama \
         --model qwen2.5:32b                     # specific Ollama model
  python pipeline.py --stage 1                   # run only stage 1
  python pipeline.py --from-stage 3             # resume from stage 3
  python pipeline.py --validate-only            # validate existing outputs

Requirements (Anthropic):
  pip install anthropic jsonschema
  export ANTHROPIC_API_KEY=sk-...

Requirements (Ollama):
  pip install openai jsonschema
  ollama serve                  # must be running
  ollama pull qwen2.5:32b       # or whichever model you choose
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import prompts
import validator

# ── Config ────────────────────────────────────────────────────────────────────

# Anthropic defaults
ANTHROPIC_MODEL   = "claude-opus-4-6"

# Ollama defaults — change to whichever model you have pulled
OLLAMA_MODEL      = "qwen2.5:32b"
OLLAMA_BASE_URL   = "http://localhost:11434/v1"

MAX_TOKENS        = 8192
MAX_RETRIES       = 3          # local models need more retries than Claude

OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

PATHS = {
    "world_state":  OUTPUT_DIR / "world_state.json",
    "event_stream": OUTPUT_DIR / "event_stream.json",
    "note_corpus":  OUTPUT_DIR / "note_corpus.json",
    "qa_set":       OUTPUT_DIR / "qa_set.json",
}

# ── Backend clients ───────────────────────────────────────────────────────────

def get_anthropic_client():
    try:
        import anthropic
    except ImportError:
        sys.exit("❌  anthropic package not installed. Run: pip install anthropic")
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        sys.exit("❌  ANTHROPIC_API_KEY not set. Export it and retry.")
    return ("anthropic", anthropic.Anthropic(api_key=key))


def get_ollama_client(model: str):
    try:
        import openai
    except ImportError:
        sys.exit("❌  openai package not installed. Run: pip install openai")
    client = openai.OpenAI(
        base_url=OLLAMA_BASE_URL,
        api_key="ollama",   # required by openai SDK but ignored by Ollama
    )
    return ("ollama", client, model)


# ── Core LLM call (backend-agnostic) ─────────────────────────────────────────

def call_model(backend_tuple: tuple, system: str, user: str, label: str) -> dict:
    """
    Call the configured backend and return parsed JSON.
    Retries up to MAX_RETRIES times on JSON parse failure.
    """
    backend = backend_tuple[0]
    print(f"\n  → [{backend}] Calling model for {label}…", flush=True)

    for attempt in range(1, MAX_RETRIES + 1):
        # ── Anthropic ──────────────────────────────────────────────────────
        if backend == "anthropic":
            _, client = backend_tuple
            import anthropic
            response = client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            raw = response.content[0].text.strip()

        # ── Ollama (OpenAI-compatible) ─────────────────────────────────────
        elif backend == "ollama":
            _, client, model = backend_tuple
            response = client.chat.completions.create(
                model=model,
                max_tokens=MAX_TOKENS,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
            )
            raw = response.choices[0].message.content.strip()

        else:
            sys.exit(f"❌  Unknown backend: {backend}")

        # ── strip accidental markdown fences ──────────────────────────────
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$",          "", raw)

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            print(f"  ⚠️  JSON parse failed (attempt {attempt}/{MAX_RETRIES}): {exc}")
            if attempt == MAX_RETRIES:
                debug_path = OUTPUT_DIR / f"{label}_raw_attempt{attempt}.txt"
                debug_path.write_text(raw)
                sys.exit(
                    f"❌  Could not parse JSON after {MAX_RETRIES} attempts.\n"
                    f"    Raw output saved to: {debug_path}\n"
                    f"    Tip: if using Ollama, try a larger model (≥32B)."
                )

    raise RuntimeError("Unexpected exit from call_model retry loop")


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


# ── Stages ────────────────────────────────────────────────────────────────────

def stage1_world_state(backend: tuple) -> dict:
    print("\n── Stage 1: World State Generation ─────────────────────────────────")
    data = call_model(backend, prompts.STAGE1_SYSTEM, prompts.STAGE1_USER, "world_state")
    errors = validator.validate_world_state(data)
    if errors:
        print("  ⚠️  Validation issues:")
        for e in errors:
            print(e)
        print("  Continuing — fix outputs/world_state.json manually if needed.")
    save(data, "world_state")
    return data


def stage2_event_stream(backend: tuple, world_state: dict) -> dict:
    print("\n── Stage 2: Event Stream Generation ────────────────────────────────")
    ws_json = json.dumps(world_state, indent=2)
    data = call_model(
        backend,
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


def stage3_note_corpus(backend: tuple, world_state: dict, event_stream: dict) -> dict:
    print("\n── Stage 3: Note Corpus Generation ─────────────────────────────────")
    events_json = json.dumps(event_stream, indent=2)
    data = call_model(
        backend,
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


def stage4_qa_set(backend: tuple, note_corpus: dict) -> dict:
    print("\n── Stage 4: QA Set Generation ───────────────────────────────────────")
    notes_json = json.dumps(note_corpus, indent=2)
    data = call_model(
        backend,
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

    p.add_argument(
        "--backend", choices=["anthropic", "ollama"], default="anthropic",
        help="LLM backend to use (default: anthropic)",
    )
    p.add_argument(
        "--model", default=None,
        help=(
            "Override the model name. "
            "Anthropic default: claude-opus-4-6  "
            "Ollama default: qwen2.5:32b"
        ),
    )

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

    # ── Build backend tuple ───────────────────────────────────────────────────
    if args.backend == "anthropic":
        backend = get_anthropic_client()
        active_model = args.model or ANTHROPIC_MODEL
        # patch the global so call_model uses the override
        global ANTHROPIC_MODEL
        ANTHROPIC_MODEL = active_model
        print(f"Backend: Anthropic  |  Model: {active_model}")

    else:  # ollama
        active_model = args.model or OLLAMA_MODEL
        backend = get_ollama_client(active_model)
        print(f"Backend: Ollama  |  Model: {active_model}  |  URL: {OLLAMA_BASE_URL}")

    # ── Determine which stages to run ─────────────────────────────────────────
    if args.stage:
        run = {args.stage}
    elif args.from_stage:
        run = set(range(args.from_stage, 5))
    else:
        run = {1, 2, 3, 4}

    print(f"Stages: {sorted(run)}")

    # ── Execute stages ────────────────────────────────────────────────────────
    world_state  = stage1_world_state(backend)            if 1 in run else load("world_state")
    event_stream = stage2_event_stream(backend, world_state)  if 2 in run else load("event_stream")
    note_corpus  = stage3_note_corpus(backend, world_state, event_stream) if 3 in run else load("note_corpus")
    if 4 in run:
        stage4_qa_set(backend, note_corpus)

    print("\n\n── Pipeline complete ─────────────────────────────────────────────────")
    print(f"  Outputs in: {OUTPUT_DIR.resolve()}")
    for key, path in PATHS.items():
        size = f"{path.stat().st_size / 1024:.1f} KB" if path.exists() else "missing"
        print(f"  {key:<16} {path.name}  ({size})")


if __name__ == "__main__":
    main()
