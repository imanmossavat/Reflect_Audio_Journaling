"""Replay scripted multi-turn sessions through the extraction call + state core, so state
DRIFT (the thing single-turn eval can't see) becomes visible. Generation is scripted in the
dataset — the single variable here is extraction + merge over a whole session.

Run:  python harness/run_session.py                       # all sessions, configured chat model
      python harness/run_session.py --session S1_charity_app --temperature 0
"""
import _bootstrap

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import ollama

from state import STAGE_NAMES, new_session
from turn import ingest_turn
from app.services.settings_service import chat_num_ctx, get_setting


def _git_short_hash() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(_bootstrap.EVAL_ROOT), text=True
        ).strip()
    except Exception:
        return "nogit"


def _extraction_chat(client, model, options):
    def chat(messages):
        resp = client.chat(model=model, messages=messages, format="json", options=options, think=False)
        return (resp.get("message", {}) or {}).get("content", "").strip()
    return chat


def _turn_path(summary: str) -> str:
    if "brief response" in (summary or ""):
        return "thin"
    if "extraction failed" in (summary or ""):
        return "failed"
    return "extracted"


def _drift_report(state, snapshots) -> dict:
    """Deterministic signals over the played session — no LLM."""
    paths = [_turn_path(s.last_turn_summary) for s in snapshots]
    visited = state.flow.completed_stages + [state.flow.current_stage]
    facts_per_stage = {st: sum(1 for f in state.facts if f.stage == st) for st in STAGE_NAMES}
    empty_visited = [st for st in visited if facts_per_stage[st] == 0 and st != state.flow.current_stage]
    prefix_ok = state.flow.completed_stages == STAGE_NAMES[:len(state.flow.completed_stages)]
    return {
        "turns": len(snapshots),
        "paths": {p: paths.count(p) for p in ("extracted", "thin", "failed")},
        "reached_stage": state.flow.current_stage,
        "completed_stages": state.flow.completed_stages,
        "session_complete": state.session_complete,
        "facts_per_stage": facts_per_stage,
        "total_facts": len(state.facts),
        "open_questions": len(state.open_questions),
        # drift flags:
        "extraction_failures": paths.count("failed"),
        "completed_in_gibbs_order": prefix_ok,
        "visited_stages_with_no_facts": empty_visited,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="sessions")
    parser.add_argument("--session", default=None, help="run only this session id")
    parser.add_argument("--model", default=None, help="override chat_model for extraction")
    parser.add_argument("--temperature", type=float, default=None, help="pass 0 to pin determinism")
    args = parser.parse_args()

    path = _bootstrap.DATASETS_DIR / args.dataset / "sessions.json"
    if not path.exists():
        print(f"{path} not found.", file=sys.stderr)
        return 1
    sessions = json.loads(path.read_text(encoding="utf-8"))["sessions"]
    if args.session:
        sessions = [s for s in sessions if s["id"] == args.session]
        if not sessions:
            print(f"session '{args.session}' not found.", file=sys.stderr)
            return 1

    model = args.model or get_setting("chat_model")
    host = get_setting("ollama_host").rstrip("/")
    options = {"num_ctx": chat_num_ctx()}
    if args.temperature is not None:
        options["temperature"] = args.temperature
    client = ollama.Client(host=host)
    chat = _extraction_chat(client, model, options)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = _bootstrap.RUNS_DIR / "sessions" / f"{stamp}_{_git_short_hash()}"
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"Replaying {len(sessions)} session(s)  model={model}  host={host}  "
          f"temperature={'(default)' if args.temperature is None else args.temperature}")

    reports = {}
    for sess in sessions:
        sid = sess["id"]
        turns = sess["turns"]
        print(f"\n=== {sid}  ({len(turns)} turns) ===")
        state = new_session(sid)
        snapshots = []
        out = run_dir / sid
        out.mkdir(exist_ok=True)
        states_f = (out / "states.jsonl").open("w", encoding="utf-8")
        for i, t in enumerate(turns, start=1):
            ingest_turn(state, t.get("user", ""), t.get("assistant", ""), i, chat)
            snap = state.model_copy(deep=True)
            snapshots.append(snap)
            states_f.write(snap.model_dump_json() + "\n")
            print(f"  [{i:2d}] {_turn_path(state.last_turn_summary):9s} "
                  f"stage={state.flow.current_stage:18s} facts={len(state.facts)}")
        states_f.close()
        (out / "state_final.json").write_text(state.model_dump_json(indent=2), encoding="utf-8")
        (out / "transcript.jsonl").write_text(
            "\n".join(json.dumps(t, ensure_ascii=False) for t in turns), encoding="utf-8")

        report = _drift_report(state, snapshots)
        reports[sid] = report
        print(f"  -> reached {report['reached_stage']}, {report['total_facts']} facts, "
              f"{report['extraction_failures']} extraction failures, "
              f"gibbs-order={report['completed_in_gibbs_order']}")
        if report["visited_stages_with_no_facts"]:
            print(f"  !! visited stages with no facts: {report['visited_stages_with_no_facts']}")

    (run_dir / "config.json").write_text(json.dumps({
        "dataset": args.dataset, "model": model, "num_ctx": chat_num_ctx(),
        "temperature": args.temperature, "timestamp": stamp, "n_sessions": len(sessions),
    }, indent=2), encoding="utf-8")
    (run_dir / "report.json").write_text(json.dumps(reports, indent=2), encoding="utf-8")
    print(f"\nRun folder: {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
