"""Run every case in a dataset through the REAL facilitator prompt + the production Ollama call.

For each case we call the same prompt builder the route uses
(`gibbs_facilitator_prompt.build_messages`) and then the same Ollama chat call
`POST /generate-question` makes in `Backend/app/routes/query.py` — model = chat_model,
think=False, options={"num_ctx": chat_num_ctx()}, no temperature set (production default).
The safety guard is intentionally out of scope here (separate guardrail); we capture the
raw facilitator turn, which is where the leak / quality signal lives.

Run:  python harness/run_eval.py --dataset facilitator
      python harness/run_eval.py --dataset facilitator --temperature 0   # pin determinism while iterating
      python harness/run_eval.py --dataset facilitator --model gpt-oss:20b
"""
import _bootstrap

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import ollama

import facilitator_proto
from app.services.settings_service import chat_num_ctx, get_setting

# Fields every case must define; checked up front so a malformed dataset fails fast and
# clearly instead of crashing mid-run after some cases already cost model calls.
_REQUIRED_CASE_KEYS = ("id", "category", "action", "journal_text")


def _git_short_hash() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(_bootstrap.EVAL_ROOT), text=True
        ).strip()
    except Exception:
        return "nogit"


def _make_run_dir(dataset: str, mode: str, config_extra: dict) -> tuple[Path, dict]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    git_hash = _git_short_hash()
    run_dir = _bootstrap.RUNS_DIR / dataset / f"{stamp}_{git_hash}_{mode}"
    run_dir.mkdir(parents=True, exist_ok=True)
    config = {"dataset": dataset, "timestamp": stamp, "git_hash": git_hash, **config_extra}
    return run_dir, config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="facilitator",
                        help=f"dataset under datasets/ (have: {', '.join(_bootstrap.list_datasets()) or 'none'})")
    parser.add_argument("--cases", default="cases.json", help="cases filename within the dataset dir.")
    parser.add_argument("--model", default=None, help="override chat_model from settings.json for this run.")
    parser.add_argument("--temperature", type=float, default=None,
                        help="override sampling temperature (default: unset = production default). Pass 0 to pin determinism.")
    parser.add_argument("--guarded", action="store_true",
                        help="route through the guard pipeline (input guard + hardened prompt + output guard/repair/fallback) instead of the raw build_messages+ollama path. The single-variable guard on/off comparison.")
    args = parser.parse_args()

    paths = _bootstrap.dataset_paths(args.dataset)
    cases_path = paths["dir"] / args.cases
    if not cases_path.exists():
        print(f"{cases_path} not found.", file=sys.stderr)
        return 1

    cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]
    malformed = [(i, [k for k in _REQUIRED_CASE_KEYS if k not in c])
                 for i, c in enumerate(cases, start=1)]
    malformed = [(i, missing) for i, missing in malformed if missing]
    if malformed:
        for i, missing in malformed:
            print(f"case #{i} is missing required field(s): {', '.join(missing)}", file=sys.stderr)
        return 1

    model = args.model or get_setting("chat_model")
    host = get_setting("ollama_host").rstrip("/")
    num_ctx = chat_num_ctx()
    options: dict = {"num_ctx": num_ctx}
    if args.temperature is not None:
        options["temperature"] = args.temperature

    client = ollama.Client(host=host)
    mode = "guarded" if args.guarded else "raw"
    print(f"Running {len(cases)} cases  mode={mode}  model={model}  host={host}  num_ctx={num_ctx}  "
          f"temperature={'(default)' if args.temperature is None else args.temperature}")

    rows: list[dict] = []
    for i, c in enumerate(cases, start=1):
        print(f"[{i:2d}/{len(cases)}] {c['id']} ({c['category']}/{c['action']}/s{c.get('step')})...", flush=True)
        guard_trace = None
        system_prompt = None
        try:
            if args.guarded:
                reply, guard_trace = facilitator_proto.generate_guarded(client, model, c, options)
                system_prompt = guard_trace.pop("system_prompt", None)
            else:
                messages = facilitator_proto.build_messages_plain(c)
                system_prompt = messages[0]["content"]
                reply = facilitator_proto._chat(client, model, messages, options)
        except Exception as exc:
            print(f"    FAILED: {exc}", file=sys.stderr)
            reply = f"<ERROR: {exc}>"

        rows.append({
            "id": c["id"],
            "category": c["category"],
            "action": c["action"],
            "step": c.get("step"),
            "journal_text": c["journal_text"],
            "history": c.get("history") or [],
            "goal": c.get("goal"),
            "scope_items": c.get("scope_items") or [],
            "risk": c.get("risk") or [],
            "expectation": c.get("expectation", ""),
            "generated_reply": reply,
            "system_prompt": system_prompt,
            "guard": guard_trace,
        })

    run_dir, config = _make_run_dir(args.dataset, mode, {
        "cases": args.cases,
        "mode": mode,
        "model": model,
        "num_ctx": num_ctx,
        "temperature": args.temperature,
        "thinking": False,
        "n_cases": len(rows),
    })

    # jsonl keeps the full structured row (the judge + report read this).
    raw_jsonl = run_dir / "raw.jsonl"
    with raw_jsonl.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # csv is a flat human-skim view (lists collapsed, long text length-only).
    raw_csv = run_dir / "raw.csv"
    flat_fields = ["id", "category", "action", "step", "goal", "scope_items",
                   "history_turns", "journal_chars", "risk", "generated_reply"]
    with raw_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=flat_fields)
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "id": r["id"],
                "category": r["category"],
                "action": r["action"],
                "step": r["step"],
                "goal": r["goal"] or "",
                "scope_items": " | ".join(r["scope_items"]),
                "history_turns": len(r["history"]),
                "journal_chars": len(r["journal_text"]),
                "risk": "|".join(r["risk"]),
                "generated_reply": r["generated_reply"],
            })

    (run_dir / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(f"\nWrote {len(rows)} rows to {raw_jsonl}")
    print(f"Run folder: {run_dir}")
    print(f"Next: python harness/judge.py --results-dir {run_dir.relative_to(_bootstrap.EVAL_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
