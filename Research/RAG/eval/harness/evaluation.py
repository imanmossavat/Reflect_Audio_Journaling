"""Single evaluation front door for a run folder.

Consolidates the three concerns that used to be separate scripts:
  - retrieval + state-aware answer metrics  (was metrics.py)
  - LLM-as-judge failure-mode labelling      (was judge.py)
  - failure-mode report                       (was report.py)

into one module with a small API:
  - evaluate(run_dir, questions_path, world_path, k)  -> (summary, counts, buckets)
       writes summary.csv + answers.csv  (the consistent evaluation output)
  - run_judge(run_dir, model, host)                   -> writes judged.csv
  - report(run_dir)                                   -> writes failure_modes.csv

The deterministic metric/scoring functions live in `metrics` and the judge prompt in
`judge`; this module composes them so callers (and `run_experiment.py`) import one thing.
A CLI mirrors the old metrics.py so it stays a drop-in:
    python harness/evaluation.py --results-dir runs/stateful/<ts>_<hash> [--k 5] [--judge]
"""
import _bootstrap  # noqa: F401  (sys.path + chroma isolation; harmless for pure metrics)

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import metrics
import judge as _judge
from app.services.settings_service import get_setting


# --------------------------------------------------------------------------- metrics

def evaluate(run_dir: Path, questions_path: Path, world_path: Path, k: int = 5) -> tuple[dict, Counter, dict]:
    """Score a run: retrieval metrics + state-aware answer accuracy.

    Writes summary.csv (retrieval + answer metrics merged) and answers.csv into run_dir,
    and returns (summary, label_counts, accuracy_buckets).
    """
    raw_jsonl = run_dir / "raw.jsonl"
    _, summary = metrics.summarize(raw_jsonl, k)

    counts: Counter = Counter()
    buckets: dict = {}
    if questions_path and Path(questions_path).exists():
        per_ans, asummary, counts, buckets = metrics.score_answers(
            raw_jsonl, questions_path, world_path, k)
        summary.update(asummary)
        metrics.write_answers_csv(run_dir / "answers.csv", per_ans)

    metrics.write_summary_csv(run_dir / "summary.csv", summary)
    return summary, counts, buckets


def print_summary(summary: dict, counts: Counter, buckets: dict, k: int) -> None:
    print(f"\nRetrieval metrics @k={k} ({summary.get('n_answerable')}/{summary.get('n_questions')} answerable)")
    print("-" * 48)
    for key, val in summary.items():
        print(f"{key:<24s} {val}")
    if counts:
        asummary = {
            "answer_accuracy": summary.get("answer_accuracy"),
            "n_correct": summary.get("n_correct"),
        }
        metrics.print_answer_report(asummary, counts, buckets)


# --------------------------------------------------------------------------- judge

def run_judge(run_dir: Path, model: str | None = None, host: str | None = None) -> Path:
    """Run the LLM-as-judge over raw.jsonl -> judged.csv. Returns the csv path."""
    raw_jsonl = run_dir / "raw.jsonl"
    judged_csv = run_dir / "judged.csv"
    model = model or get_setting("chat_model")
    host = host or get_setting("ollama_host")
    print(f"Judging with model={model} host={host}")

    rows = [json.loads(line) for line in raw_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    out_rows: list[dict] = []
    for i, r in enumerate(rows, start=1):
        print(f"[{i:2d}/{len(rows)}] judging {r['id']}...", flush=True)
        verdict = _judge.call_judge(model, host, r)
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
    return judged_csv


# --------------------------------------------------------------------------- report

def report(run_dir: Path) -> Path:
    """Summarize judged.csv into failure-mode counts + per-question table -> failure_modes.csv."""
    judged_csv = run_dir / "judged.csv"
    summary_csv = run_dir / "failure_modes.csv"
    rows = list(csv.DictReader(judged_csv.open(encoding="utf-8")))
    counts = Counter(r["failure_mode"] for r in rows)
    by_mode: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_mode[r["failure_mode"]].append(r)

    total = len(rows)
    print("\n" + "=" * 72)
    print(f"RAG eval — {total} questions  ({run_dir.name})")
    print("=" * 72)
    print(f"{'failure_mode':<30s} {'count':>5s}  {'%':>5s}")
    print("-" * 72)
    for mode, n in counts.most_common():
        print(f"{mode:<30s} {n:>5d}  {n*100/total:>4.0f}%")

    print("\n" + "=" * 72)
    print("Where the RAG goes wrong (non-CORRECT, grouped by failure mode)")
    print("=" * 72)
    for mode, items in by_mode.items():
        if mode == "CORRECT":
            continue
        print(f"\n[{mode}] — {len(items)} question(s)")
        for r in items:
            print(f"  {r['id']}: {r['question']}")
            print(f"     -> {r['rationale']}")

    with summary_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["failure_mode", "count", "percent"])
        for mode, n in counts.most_common():
            writer.writerow([mode, n, f"{n*100/total:.1f}"])
    print(f"\nWrote summary to {summary_csv}")
    return summary_csv


# --------------------------------------------------------------------------- CLI

def _resolve_dataset_paths(run_dir: Path) -> tuple[Path | None, Path | None]:
    """Read the run's config.json to locate its dataset's questions.json + world_state.json."""
    config_path = run_dir / "config.json"
    if not config_path.exists():
        return None, None
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    ds_dir = _bootstrap.DATASETS_DIR / cfg.get("dataset", "")
    return ds_dir / cfg.get("questions", "questions.json"), ds_dir / "world_state.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", required=True, help="a single run folder, e.g. runs/stateful/<ts>_<hash>")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--judge", action="store_true", help="also run the LLM-as-judge + failure-mode report")
    parser.add_argument("--model", default=None, help="judge model (default: chat_model from settings)")
    args = parser.parse_args()

    run_dir = Path(args.results_dir)
    if not (run_dir / "raw.jsonl").exists():
        print(f"{run_dir / 'raw.jsonl'} not found. Run run_experiment.py first.", file=sys.stderr)
        return 1

    questions_path, world_path = _resolve_dataset_paths(run_dir)
    summary, counts, buckets = evaluate(run_dir, questions_path, world_path, args.k)
    print_summary(summary, counts, buckets, args.k)
    print(f"Wrote {run_dir / 'summary.csv'}")

    if args.judge:
        run_judge(run_dir, model=args.model)
        report(run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
