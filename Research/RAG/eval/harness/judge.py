"""LLM-as-judge: classify each (question, retrieved_context, answer) into a
failure mode and emit a one-sentence rationale.

Input:  <results-dir>/raw.jsonl   (gold_supporting_notes are embedded in each row)
Output: <results-dir>/judged.csv

Run: python harness/judge.py --results-dir runs/baseline/<ts>_<hash> [--model gpt-oss:20b]
"""
import _bootstrap

import argparse
import csv
import json
import sys
from pathlib import Path

import ollama

from app.services.settings_service import get_setting

LABELS = [
    "CORRECT",
    "RETRIEVAL_MISS",
    "PARTIAL_RETRIEVAL",
    "GENERATION_OVERREACH",
    "GENERATION_HALLUCINATION",
    "FAILED_REFUSAL",
    "INCORRECT_REFUSAL",
    "CONTRADICTS_NOTES",
]

JUDGE_PROMPT = """You are evaluating a RAG (retrieval-augmented generation) system's answer to a question about the user's personal notes. Classify the failure mode using ONE of these labels, then give a one-sentence rationale grounded in the data shown to you. Do not invent facts that aren't in the inputs.

LABELS:
- CORRECT: answer matches expected substance and is supported by the retrieved context. If the question is unanswerable from the notes, a clear refusal ("I don't know based on the notes" or equivalent) is also CORRECT.
- RETRIEVAL_MISS: none of the gold supporting note_ids appear in the retrieved_note_ids list. (Only applies to answerable questions with non-empty gold notes.)
- PARTIAL_RETRIEVAL: some but not all gold supporting note_ids retrieved, AND the answer is missing facts that would have been in the missing notes.
- GENERATION_OVERREACH: the right notes were retrieved, but the answer adds psychological, causal, or diagnostic inference beyond what the notes literally say (e.g. "this reflects a systemic pattern", or asserting a state is "current"/"former" when the notes don't license it).
- GENERATION_HALLUCINATION: the answer states a concrete fact (name, number, date, event detail) that is NOT in any retrieved chunk and NOT in the expected answer.
- FAILED_REFUSAL: question's answerability is "unanswerable" but the answer asserts a specific answer instead of refusing.
- INCORRECT_REFUSAL: the answer refuses or hedges ("I don't know", "not enough information") when the retrieved context actually contains the answer.
- CONTRADICTS_NOTES: the answer states something the retrieved chunks explicitly contradict.

Output STRICT JSON only, no markdown:
{{"failure_mode": "<LABEL>", "rationale": "<one sentence>"}}

INPUTS:
- question: {question}
- answerability: {answerability}
- gold_supporting_notes: {gold}
- retrieved_note_ids (in rank order): {retrieved}
- expected_answer: {expected}
- generated_answer: {generated}
- retrieved_context:
---
{context}
---
"""


def call_judge(model: str, host: str, payload: dict) -> dict:
    prompt = JUDGE_PROMPT.format(
        question=payload["question"],
        answerability=payload["answerability"],
        gold=payload["gold_supporting_notes"] or "(none — unanswerable)",
        retrieved=payload["retrieved_note_ids"] or "(none)",
        expected=payload["expected_answer"],
        generated=payload["generated_answer"],
        context=payload["retrieved_texts"] or "(empty)",
    )
    client = ollama.Client(host=host)
    response = client.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        format="json",
        options={"temperature": 0.0},
    )
    content = response.get("message", {}).get("content", "").strip()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return {"failure_mode": "JUDGE_PARSE_ERROR", "rationale": content[:200]}
    label = data.get("failure_mode", "JUDGE_PARSE_ERROR")
    if label not in LABELS and label != "JUDGE_PARSE_ERROR":
        return {"failure_mode": "JUDGE_PARSE_ERROR", "rationale": f"unknown label: {label}"}
    return {"failure_mode": label, "rationale": data.get("rationale", "")[:400]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", required=True, help="run folder containing raw.jsonl")
    parser.add_argument("--model", default=None, help="judge model (default: chat_model from settings)")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    raw_jsonl = results_dir / "raw.jsonl"
    judged_csv = results_dir / "judged.csv"
    if not raw_jsonl.exists():
        print(f"{raw_jsonl} not found. Run run_eval.py first.", file=sys.stderr)
        return 1

    model = args.model or get_setting("chat_model")
    host = get_setting("ollama_host")
    print(f"Judging with model={model} host={host}")

    rows = [json.loads(line) for line in raw_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    out_rows: list[dict] = []
    for i, r in enumerate(rows, start=1):
        print(f"[{i:2d}/{len(rows)}] judging {r['id']}...", flush=True)
        verdict = call_judge(model, host, r)
        out_rows.append({
            "id": r["id"],
            "question": r["question"],
            "answerability": r["answerability"],
            "gold_supporting_notes": r["gold_supporting_notes"],
            "retrieved_note_ids": r["retrieved_note_ids"],
            "expected_answer": r["expected_answer"],
            "generated_answer": r["generated_answer"],
            "failure_mode": verdict["failure_mode"],
            "rationale": verdict["rationale"],
        })

    with judged_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"Wrote {len(out_rows)} rows to {judged_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
