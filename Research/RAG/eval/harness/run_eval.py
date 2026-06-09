"""Run every question in a dataset's question set through the production RAG.

Run:  python harness/run_eval.py --dataset baseline --top-k 5
      python harness/run_eval.py --dataset baseline --questions questions_multi.json --reranker
      python harness/run_eval.py --dataset stateful --reranker
"""
import _bootstrap

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import metrics
from app.services import rag as rag_module
from app.services import reranker as reranker_module
from app.services.rag import query_sources
from app.services.settings_service import get_setting


def _apply_eval_isolation(use_reranker: bool) -> None:
    """The synthetic source_ids collide with real SQLite rows, so neutralize recency
    (get_sources_meta -> {}). With the reranker off, relevance falls back to the
    embedding score, giving a clean reranker-on vs -off comparison under one code path.

    NOTE (stateful set): to measure recency-vs-relevance you must give the eval its own
    SQLite and stop neutralizing here -- see GUIDE 'recency' section."""
    rag_module.get_sources_meta = lambda *a, **k: {}
    if not use_reranker:
        reranker_module.rerank = lambda question, nodes: [
            (n, float(getattr(n, "score", 0.0) or 0.0)) for n in nodes
        ]


def _git_short_hash() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(_bootstrap.EVAL_ROOT), text=True
        ).strip()
    except Exception:
        return "nogit"


def _make_run_dir(dataset: str, top_k: int, reranker: bool, questions: str,
                  thinking: bool) -> tuple[Path, dict]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    git_hash = _git_short_hash()
    run_dir = _bootstrap.RUNS_DIR / dataset / f"{stamp}_{git_hash}"
    run_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "dataset": dataset,
        "timestamp": stamp,
        "git_hash": git_hash,
        "top_k": top_k,
        "reranker": reranker,
        "thinking_enabled": thinking,
        "questions": questions,
        "embed_model": get_setting("embed_model"),
        "chat_model": get_setting("chat_model"),
    }
    return run_dir, config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="baseline",
                        help=f"dataset name under datasets/ (have: {', '.join(_bootstrap.list_datasets()) or 'none'})")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--reranker", action="store_true", help="Record reranker=on in this run's config.")
    thinking_grp = parser.add_mutually_exclusive_group()
    thinking_grp.add_argument("--thinking", dest="thinking", action="store_true", default=None,
                              help="Force thinking ON for this run (overrides settings.json).")
    thinking_grp.add_argument("--no-thinking", dest="thinking", action="store_false",
                              help="Force thinking OFF for this run (overrides settings.json).")
    parser.add_argument("--questions", default="questions.json",
                        help="Question set filename within the dataset dir (e.g. questions_multi.json).")
    args = parser.parse_args()

    paths = _bootstrap.use_dataset(args.dataset)
    index_map_path = paths["index"]
    questions_path = paths["dir"] / args.questions

    if not index_map_path.exists():
        print(f"{index_map_path} not found. Run: python harness/ingest.py --dataset {args.dataset}", file=sys.stderr)
        return 1
    if not questions_path.exists():
        print(f"{questions_path} not found.", file=sys.stderr)
        return 1

    questions = json.loads(questions_path.read_text(encoding="utf-8"))["questions"]
    source_to_note = {int(k): v for k, v in json.loads(index_map_path.read_text(encoding="utf-8")).items()}

    _apply_eval_isolation(args.reranker)

    # Resolve the thinking toggle: CLI flag overrides settings.json for this run only.
    requested_thinking = get_setting("thinking_enabled") if args.thinking is None else args.thinking
    rag_module._thinking_enabled = lambda: bool(requested_thinking)
    # Effective = requested AND the chat model actually supports thinking.
    effective_thinking = bool(requested_thinking) and rag_module.model_supports_thinking(get_setting("chat_model"))
    rag_module.configure_llamaindex()  # rebuild the LLM with the resolved thinking flag

    run_dir, config = _make_run_dir(args.dataset, args.top_k, args.reranker, args.questions, effective_thinking)
    raw_csv = run_dir / "raw.csv"
    raw_jsonl = run_dir / "raw.jsonl"

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

    (run_dir / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    _, summary = metrics.summarize(raw_jsonl, args.top_k)

    # State-aware answer scoring (CORRECT / INCORRECT_REFUSAL / WRONG_STATE / ...) bucketed by
    # state_role + trap_type. Needs the dataset's questions.json + world_state.json.
    per_ans, asummary, counts, buckets = metrics.score_answers(
        raw_jsonl, questions_path, paths["world"], args.top_k)
    summary.update(asummary)
    metrics.write_answers_csv(run_dir / "answers.csv", per_ans)
    metrics.write_summary_csv(run_dir / "summary.csv", summary)

    print(f"Wrote {len(rows)} rows to {raw_csv}")
    print(f"Run folder: {run_dir}")
    print(f"P@{args.top_k}={summary[f'precision_at_{args.top_k}']}  "
          f"R@{args.top_k}={summary[f'recall_at_{args.top_k}']}  MRR={summary['mrr']}")
    metrics.print_answer_report(asummary, counts, buckets)
    return 0


if __name__ == "__main__":
    sys.exit(main())
