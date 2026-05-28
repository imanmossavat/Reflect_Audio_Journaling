"""Interactive REPL — ask questions about your own journals.

Loads the source_id -> filename map written by ingest.py, then loops:
prompt for a question, run RAG, print the generated answer plus which
journal each retrieved chunk came from. Type :q or quit (or empty input)
to exit.

Run: python ask.py [--top-k 5]
"""
import _bootstrap

import argparse
import json
import sys
from pathlib import Path

from app.services.rag import query_sources

HERE = Path(__file__).resolve().parent
INDEX_MAP_PATH = HERE / "sources_index.json"

EXCERPT_CHARS = 300


def _excerpt(text: str) -> str:
    text = (text or "").strip().replace("\n", " ")
    if len(text) <= EXCERPT_CHARS:
        return text
    return text[:EXCERPT_CHARS].rstrip() + "..."


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    if not INDEX_MAP_PATH.exists():
        print(f"{INDEX_MAP_PATH} not found. Run `python ingest.py` first.", file=sys.stderr)
        return 1

    source_to_filename = {
        int(k): v for k, v in json.loads(INDEX_MAP_PATH.read_text(encoding="utf-8")).items()
    }
    print(f"Loaded {len(source_to_filename)} indexed journal(s). Type :q to exit.\n")

    while True:
        try:
            question = input("Question> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not question or question.lower() in {":q", "quit", "exit"}:
            return 0

        try:
            result = query_sources(question, top_k=args.top_k)
        except Exception as exc:
            print(f"  ERROR: {exc}\n", file=sys.stderr)
            continue

        answer = (result.get("answer") or "").strip()
        print(f"\nAnswer:\n  {answer}\n")

        sources = result.get("sources", []) or []
        if not sources:
            print("  (no sources returned)\n")
            continue

        print("Sources:")
        for i, src in enumerate(sources, start=1):
            sid = src.get("source_id")
            try:
                sid_int = int(sid) if sid is not None else None
            except (TypeError, ValueError):
                sid_int = None
            filename = source_to_filename.get(sid_int, f"unknown(source_id={sid})")
            score = float(src.get("score") or 0.0)
            print(f"  {i}. {filename}  ·  score={score:.4f}")
            print(f"     {_excerpt(src.get('text', ''))}")
        print()


if __name__ == "__main__":
    sys.exit(main())
