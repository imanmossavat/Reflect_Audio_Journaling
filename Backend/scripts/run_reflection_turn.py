#!/usr/bin/env python
"""Manual prompt-quality iteration for the Phase 2a reflection loop.

Drives a real, multi-turn conversation through app.services.reflectionLoop
against a real Ollama call and prints the facilitator's reply plus the
resulting Gist/Open Thread after each turn — the same "build_messages ->
production model call -> raw output" pattern
Research/Reflection/eval/harness/run_eval.py already uses, pointed at the
new Document B §5/§6 prompts instead of the old stage-gated ones.

Usage:
    uv run python scripts/run_reflection_turn.py --source path/to/entry.txt --focus "explore why the deadline slipped"

Then type student messages at the prompt; Ctrl-D or an empty line to stop.
Prefix a line with "ok"/"yes"/etc. to see the thin-turn gate skip Update.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.reflectionLoop import Focus, ReflectionState, run_turn  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Path to a journal entry text file")
    parser.add_argument("--focus", required=True, help="The student's stated focus for this session")
    parser.add_argument("--chat-model", default=None, help="Override the configured chat_model setting")
    args = parser.parse_args()

    source_text = Path(args.source).read_text()
    included_sources = [{"source_id": "1", "text": source_text}]

    state = ReflectionState(chat_id="dev-script", focus=Focus(value=args.focus))

    print(f"--- session start (focus: {args.focus!r}) ---\n")
    turn = 0
    student_message = ""  # opening turn has no student message yet
    while True:
        result = run_turn(state, student_message, included_sources, chat_model=args.chat_model)
        state = result.state
        turn += 1
        print(f"[turn {turn}] Facilitator: {result.reply}\n")
        print(f"  updated={result.updated}  gist={state.gist.text!r}")
        print(f"  open_thread={state.open_thread.text!r}")
        if result.focus_shift_suggested:
            print(f"  focus_shift_suggested={result.focus_shift_suggested!r}")
        print()

        try:
            student_message = input("You: ").strip()
        except EOFError:
            break
        if not student_message:
            break

    print("\n--- final state ---")
    print(json.dumps(state.model_dump(), indent=2))


if __name__ == "__main__":
    main()
