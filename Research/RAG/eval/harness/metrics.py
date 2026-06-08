"""Metrics over a run's raw.jsonl.

Two layers:
  1. RETRIEVAL (deterministic, gold note ids): Precision@K, Recall@K, MRR, context recall/precision.
  2. ANSWER (state-aware): classify each generated answer and bucket accuracy by state_role / trap_type.
     Needs the dataset's questions.json (aliases/state_role/trap_type) + world_state.json (to detect
     WRONG_STATE = naming a competing value of the SAME state variable).

Answer labels:
  CORRECT            answerable, all expected alias(es) present.
  PARTIAL            answerable, multi-part answer with only some parts present.
  INCORRECT_REFUSAL  answerable, said "I don't know", BUT a gold note WAS retrieved -> generation fault.
  REFUSAL_NO_CONTEXT answerable, said "I don't know", and no gold note retrieved -> retrieval fault.
  WRONG_STATE        answerable, named a competing value of the same state variable (e.g. current job
                     when 'former' was asked) instead of the expected one.
  WRONG_OTHER        answerable, wrong but not a recognizable competing-state value.
  CORRECT_REFUSAL    unanswerable, correctly refused.
  FAILED_REFUSAL     unanswerable, asserted an answer instead of refusing.

Importable (summarize / score_answers) and runnable against one run folder:
    python harness/metrics.py --results-dir runs/stateful/<ts>_<hash> [--k 5]
"""
import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

EVAL_ROOT = Path(__file__).resolve().parent.parent  # eval/


# --------------------------------------------------------------------------- retrieval

def parse_pipe(value) -> list[str]:
    """Pipe-joined string (or list) -> list of non-empty ids."""
    if isinstance(value, list):
        items = value
    else:
        items = (value or "").split("|")
    return [s.strip() for s in items if s and s.strip()]


def per_question_metrics(gold: list[str], retrieved: list[str], k: int) -> dict:
    top = retrieved[:k]
    gold_set = set(gold)
    hits = [r for r in top if r in gold_set]
    rank = next((i + 1 for i, r in enumerate(top) if r in gold_set), None)
    return {
        "precision_at_k": len(hits) / len(top) if top else 0.0,
        "recall_at_k": len(hits) / len(gold_set) if gold_set else None,
        "mrr": 1.0 / rank if rank else 0.0,
        "hit": bool(hits),
    }


def load_raw_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def summarize(raw_path: Path, k: int) -> tuple[list[dict], dict]:
    rows = load_raw_jsonl(raw_path)
    per_q: list[dict] = []
    for r in rows:
        gold = parse_pipe(r.get("gold_supporting_notes"))
        retrieved = parse_pipe(r.get("retrieved_note_ids"))
        answerable = r.get("answerability") == "answerable" and bool(gold)
        m = per_question_metrics(gold, retrieved, k)
        per_q.append({"id": r.get("id"), "answerable": answerable, **m,
                      "said_idk": is_refusal(r.get("generated_answer"))})

    answerable_rows = [q for q in per_q if q["answerable"]]
    unanswerable_rows = [q for q in per_q if not q["answerable"]]
    summary = {
        "k": k,
        "n_questions": len(per_q),
        "n_answerable": len(answerable_rows),
        f"precision_at_{k}": round(mean(q["precision_at_k"] for q in answerable_rows), 4) if answerable_rows else None,
        f"recall_at_{k}": round(mean(q["recall_at_k"] for q in answerable_rows), 4) if answerable_rows else None,
        "mrr": round(mean(q["mrr"] for q in answerable_rows), 4) if answerable_rows else None,
        "context_recall": round(mean(1.0 if q["hit"] else 0.0 for q in answerable_rows), 4) if answerable_rows else None,
        "context_precision": round(mean(q["precision_at_k"] for q in answerable_rows), 4) if answerable_rows else None,
        "unanswerable_idk_rate": round(mean(1.0 if q["said_idk"] else 0.0 for q in unanswerable_rows), 4) if unanswerable_rows else None,
    }
    return per_q, summary


def write_summary_csv(path: Path, summary: dict) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        for key, val in summary.items():
            writer.writerow([key, val])


# --------------------------------------------------------------------------- answer scoring

def _norm(s: str) -> str:
    """Lowercase, strip punctuation to spaces, collapse whitespace."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", (s or "").lower())).strip()


def is_refusal(text: str) -> bool:
    t = (text or "").strip().lower().replace("’", "'")
    return (
        t.startswith(("i don't know", "i do not know", "i dont know"))
        or "don't know based on the notes" in t
        or "do not know based on the notes" in t
    )


def _is_conjunct(qmeta: dict) -> bool:
    """Multi-part answer where ALL aliases must appear (vs synonyms where ANY suffices)."""
    role = qmeta.get("state_role", "") or ""
    return "+" in role or role in ("mixed", "full_history")


def _answer_status(qmeta: dict, gen_norm: str) -> str:
    """'full' | 'partial' | 'none' against the expected alias(es)."""
    aliases = qmeta.get("aliases") or [qmeta.get("expected_answer", "")]
    present = [a for a in aliases if _norm(a) and _norm(a) in gen_norm]
    if _is_conjunct(qmeta):
        if aliases and len(present) == len(aliases):
            return "full"
        return "partial" if present else "none"
    return "full" if present else "none"


def build_state_index(world_path: Path) -> dict[str, set[str]]:
    """var_id -> set of normalized alias strings for every value of that state variable
    (timeline values + their aliases + non_state_mentions). Used to spot WRONG_STATE."""
    index: dict[str, set[str]] = {}
    if not world_path or not Path(world_path).exists():
        return index
    world = json.loads(Path(world_path).read_text(encoding="utf-8"))
    for sv in world.get("state_variables", []):
        names: set[str] = set()
        for item in sv.get("timeline", []) + sv.get("non_state_mentions", []):
            value = (item.get("value") or "").strip()
            # skip placeholder/non-entity values like "(unemployed / job searching)"
            if value and not value.startswith("("):
                names.add(_norm(value))
            for a in item.get("aliases", []):
                names.add(_norm(a))
        index[sv["var_id"]] = {n for n in names if n}
    return index


def classify_answer(qmeta: dict, row: dict, state_index: dict[str, set[str]], k: int) -> str:
    gen = row.get("generated_answer", "") or ""
    gen_norm = _norm(gen)

    if qmeta.get("answerability") == "unanswerable":
        return "CORRECT_REFUSAL" if is_refusal(gen) else "FAILED_REFUSAL"

    # answerable
    if is_refusal(gen):
        gold = set(parse_pipe(row.get("gold_supporting_notes")))
        retrieved = set(parse_pipe(row.get("retrieved_note_ids"))[:k])
        return "INCORRECT_REFUSAL" if (gold & retrieved) else "REFUSAL_NO_CONTEXT"

    status = _answer_status(qmeta, gen_norm)
    if status == "full":
        return "CORRECT"
    if status == "partial":
        return "PARTIAL"

    # wrong: did it name a competing value of the SAME state variable?
    expected = {_norm(a) for a in (qmeta.get("aliases") or [qmeta.get("expected_answer", "")]) if _norm(a)}
    for names in state_index.values():
        if expected & names:  # this variable owns the expected answer
            competing = names - expected
            if any(c and c in gen_norm for c in competing):
                return "WRONG_STATE"
            break
    return "WRONG_OTHER"


CORRECT_LABELS = {"CORRECT", "CORRECT_REFUSAL"}


def score_answers(raw_path: Path, questions_path: Path, world_path: Path, k: int) -> tuple[list[dict], dict, Counter, dict]:
    rows = {r["id"]: r for r in load_raw_jsonl(raw_path)}
    qmetas = json.loads(Path(questions_path).read_text(encoding="utf-8"))["questions"]
    state_index = build_state_index(world_path)

    per: list[dict] = []
    for q in qmetas:
        r = rows.get(q["id"], {})
        label = classify_answer(q, r, state_index, k)
        gold = set(parse_pipe(r.get("gold_supporting_notes")))
        retrieved = set(parse_pipe(r.get("retrieved_note_ids"))[:k])
        per.append({
            "id": q["id"],
            "answerability": q.get("answerability"),
            "state_role": q.get("state_role"),
            "trap_type": q.get("trap_type"),
            "required_hops": q.get("required_hops"),
            "gold_hit": bool(gold & retrieved) if gold else None,
            "label": label,
            "expected_answer": q.get("expected_answer", ""),
            "generated_answer": (r.get("generated_answer", "") or "").replace("\n", " "),
        })

    counts = Counter(p["label"] for p in per)
    answerable = [p for p in per if p["answerability"] == "answerable"]
    n_correct = sum(1 for p in answerable if p["label"] == "CORRECT")
    asummary = {
        "answer_accuracy": round(n_correct / len(answerable), 4) if answerable else None,
        "n_correct": n_correct,
        "incorrect_refusals": counts.get("INCORRECT_REFUSAL", 0),
        "refusals_no_context": counts.get("REFUSAL_NO_CONTEXT", 0),
        "wrong_state": counts.get("WRONG_STATE", 0),
        "wrong_other": counts.get("WRONG_OTHER", 0),
        "partial": counts.get("PARTIAL", 0),
        "failed_refusals": counts.get("FAILED_REFUSAL", 0),
    }

    def bucket(key: str) -> dict:
        acc: dict = defaultdict(lambda: [0, 0])
        for p in answerable:
            acc[p[key] or "?"][1] += 1
            if p["label"] == "CORRECT":
                acc[p[key] or "?"][0] += 1
        return {k2: f"{v[0]}/{v[1]}" for k2, v in sorted(acc.items())}

    buckets = {"by_state_role": bucket("state_role"), "by_trap_type": bucket("trap_type")}
    return per, asummary, counts, buckets


def write_answers_csv(path: Path, per: list[dict]) -> None:
    cols = ["id", "answerability", "state_role", "trap_type", "required_hops",
            "gold_hit", "label", "expected_answer", "generated_answer"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for p in per:
            writer.writerow({c: p.get(c, "") for c in cols})


def print_answer_report(asummary: dict, counts: Counter, buckets: dict) -> None:
    print("\nAnswer scoring")
    print("-" * 48)
    print(f"answer_accuracy (CORRECT / answerable) {asummary['answer_accuracy']}  ({asummary['n_correct']} correct)")
    for label, n in counts.most_common():
        print(f"  {label:<20s} {n}")
    print("  by state_role:", buckets["by_state_role"])
    print("  by trap_type :", buckets["by_trap_type"])


# --------------------------------------------------------------------------- CLI

def _resolve_dataset_paths(results_dir: Path) -> tuple[Path | None, Path | None, str]:
    """Read the run's config.json to locate its dataset's questions.json + world_state.json."""
    config_path = results_dir / "config.json"
    if not config_path.exists():
        return None, None, ""
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    ds = cfg.get("dataset", "")
    qfile = cfg.get("questions", "questions.json")
    ds_dir = EVAL_ROOT / "datasets" / ds
    return ds_dir / qfile, ds_dir / "world_state.json", ds


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", required=True,
                        help="a single run folder, e.g. runs/stateful/<ts>_<hash>")
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    raw_path = results_dir / "raw.jsonl"
    if not raw_path.exists():
        print(f"{raw_path} not found. Run run_eval.py first.", file=sys.stderr)
        return 1

    _, summary = summarize(raw_path, args.k)

    # answer scoring, if we can find the dataset's questions + world state
    questions_path, world_path, ds = _resolve_dataset_paths(results_dir)
    answer_report = None
    if questions_path and questions_path.exists():
        per, asummary, counts, buckets = score_answers(raw_path, questions_path, world_path, args.k)
        summary.update(asummary)
        write_answers_csv(results_dir / "answers.csv", per)
        answer_report = (asummary, counts, buckets)

    write_summary_csv(results_dir / "summary.csv", summary)

    print(f"\nRetrieval metrics @k={args.k} ({summary['n_answerable']}/{summary['n_questions']} answerable)")
    print("-" * 48)
    for key, val in summary.items():
        print(f"{key:<24s} {val}")

    recall, precision = summary["context_recall"], summary["context_precision"]
    print("\nGate:")
    if recall is not None and precision is not None:
        if recall >= 0.8 and precision < 0.5:
            print(f"  high recall ({recall}) + low precision ({precision}) -> reranker is the lever.")
        elif recall < 0.8:
            print(f"  low recall ({recall}) -> fix retrieval/chunking upstream, not the reranker.")
        else:
            print(f"  recall {recall}, precision {precision} -> reranker gain likely marginal.")

    if answer_report:
        print_answer_report(*answer_report)
        print(f"\nWrote {results_dir / 'answers.csv'}")
    print(f"Wrote {results_dir / 'summary.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
