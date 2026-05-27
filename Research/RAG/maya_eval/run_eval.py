"""Run every question in questions.json through the production RAG.

For each question records: generated answer, retrieved note_ids (mapped via
notes_index.json), retrieved chunk texts, similarity scores. Writes
results/raw.csv and results/raw.jsonl.

Run: python run_eval.py [--top-k 5]
"""
import _bootstrap

import argparse
import csv
import json
import sys
from pathlib import Path

from app.services.rag import query_sources

HERE = Path(__file__).resolve().parent
QUESTIONS_PATH = HERE / "questions.json"
INDEX_MAP_PATH = HERE / "notes_index.json"
RESULTS_DIR = HERE / "results"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    if not INDEX_MAP_PATH.exists():
        print(f"{INDEX_MAP_PATH} not found. Run ingest.py first.", file=sys.stderr)
        return 1

    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))["questions"]
    source_to_note = {int(k): v for k, v in json.loads(INDEX_MAP_PATH.read_text(encoding="utf-8")).items()}

    RESULTS_DIR.mkdir(exist_ok=True)
    raw_csv = RESULTS_DIR / "raw.csv"
    raw_jsonl = RESULTS_DIR / "raw.jsonl"

    rows: list[dict] = []
    for i, q in enumerate(questions, start=1):
        print(f"[{i:2d}/{len(questions)}] {q['id']}: {q['question'][:70]}...", flush=True)
        try:
            result = query_sources(q["question"], top_k=args.top_k)
        except Exception as exc:
            print(f"    FAILED: {exc}", file=sys.stderr)
            rows.append({
                "id": q["id"],
                "question": q["question"],
                "expected_answer": q["expected_answer"],
                "answerability": q["answerability"],
                "gold_supporting_notes": "|".join(q["gold_supporting_notes"]),
                "generated_answer": f"<ERROR: {exc}>",
                "retrieved_note_ids": "",
                "retrieved_scores": "",
                "retrieved_texts": "",
            })
            continue

        retrieved_note_ids: list[str] = []
        retrieved_scores: list[float] = []
        retrieved_texts: list[str] = []
        for src in result.get("sources", []):
            sid = src.get("source_id")
            note_id = source_to_note.get(int(sid)) if sid is not None else None
            retrieved_note_ids.append(note_id or f"unknown-{sid}")
            retrieved_scores.append(round(float(src.get("score") or 0.0), 4))
            retrieved_texts.append((src.get("text") or "").strip())

        rows.append({
            "id": q["id"],
            "question": q["question"],
            "expected_answer": q["expected_answer"],
            "answerability": q["answerability"],
            "gold_supporting_notes": "|".join(q["gold_supporting_notes"]),
            "generated_answer": (result.get("answer") or "").strip(),
            "retrieved_note_ids": "|".join(retrieved_note_ids),
            "retrieved_scores": "|".join(str(s) for s in retrieved_scores),
            "retrieved_texts": "\n---\n".join(retrieved_texts),
        })

    with raw_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    with raw_jsonl.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Wrote {len(rows)} rows to {raw_csv}")
    print(f"Wrote {len(rows)} rows to {raw_jsonl}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
