"""Summarise a judged run: counts per failure mode, pass-rate by category/action/stage,
and judge-vs-deterministic-check DISAGREEMENTS (the rows most worth a human glance).

Reads  <results-dir>/judged.csv  +  <results-dir>/raw.jsonl
Writes <results-dir>/report.md   (and prints the same to the console)

Run: python harness/report.py --results-dir runs/facilitator/<ts>_<hash>
"""
import _bootstrap  # noqa: F401  (sys.path side effect; keeps harness imports uniform)

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import checks
import guard


def _load(results_dir: Path) -> list[dict]:
    raw = {r["id"]: r for r in (
        json.loads(line) for line in (results_dir / "raw.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()
    )}
    with (results_dir / "judged.csv").open(encoding="utf-8") as f:
        judged = list(csv.DictReader(f))
    merged = []
    for j in judged:
        r = raw.get(j["id"], {})
        reply = r.get("generated_reply", j.get("generated_reply", ""))
        user_text = (r.get("journal_text") or "") + " " + " ".join(
            (h.get("answer") or "") for h in (r.get("history") or [])
        )
        signals = checks.run_all(reply)
        reply_leaks = set(signals["leak_tokens"])
        user_leaks = set(checks.leak_token_hits(user_text))
        merged.append({
            **j,
            "category": j.get("category") or r.get("category", ""),
            "reply": reply,
            # Same attribution the guard uses at runtime (token diff + self-disclosure) —
            # keeps the scoreboard and the guard in lock-step.
            "novel_leak": guard.novel_leak(reply, user_text),
            "echoed_leak": sorted(reply_leaks & user_leaks),  # appears in user's own text (e.g. RF17) — likely fine
            "format_violations": signals["format_violations"],
            "question_count": signals["question_count"],
            "is_thin": signals["is_thin"],
        })
    return merged


def _bar(passed: int, total: int) -> str:
    pct = (passed / total * 100) if total else 0.0
    return f"{passed}/{total} ({pct:4.0f}%)"


def _passrate_block(title: str, key: str, rows: list[dict]) -> list[str]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[str(r.get(key))].append(r)
    out = [f"### Pass rate by {title}", ""]
    for g in sorted(groups):
        grp = groups[g]
        passed = sum(1 for r in grp if r["failure_mode"] == "PASS")
        out.append(f"- `{g}` — {_bar(passed, len(grp))}")
    out.append("")
    return out


def build_report(results_dir: Path, rows: list[dict]) -> str:
    total = len(rows)
    passed = sum(1 for r in rows if r["failure_mode"] == "PASS")
    config = {}
    cfg_path = results_dir / "config.json"
    if cfg_path.exists():
        config = json.loads(cfg_path.read_text(encoding="utf-8"))
    judge_cfg = {}
    jcfg_path = results_dir / "judged_config.json"
    if jcfg_path.exists():
        judge_cfg = json.loads(jcfg_path.read_text(encoding="utf-8"))

    L: list[str] = []
    L.append(f"# Facilitator eval report — {results_dir.name}")
    L.append("")
    L.append(f"- model: `{config.get('model', '?')}`  ·  temperature: `{config.get('temperature')}`  "
             f"·  num_ctx: `{config.get('num_ctx', '?')}`  ·  git: `{config.get('git_hash', '?')}`")
    L.append(f"- judge: `{judge_cfg.get('judge_model', '?')}`  ·  mode: `{config.get('mode', '?')}`")
    L.append(f"- **overall pass rate: {_bar(passed, total)}**")
    L.append("")

    counts = Counter(r["failure_mode"] for r in rows)
    L.append("### Failure-mode counts")
    L.append("")
    from judge import LABELS  # show in severity order, including labels with 0 hits
    order = LABELS + [m for m in counts if m not in LABELS]
    for mode in order:
        if counts.get(mode):
            L.append(f"- {mode}: {counts[mode]}")
    L.append("")

    L += _passrate_block("category", "category", rows)
    L += _passrate_block("action", "action", rows)
    L += _passrate_block("stage", "step", rows)

    # --- Disagreements: deterministic check fired but judge said PASS (and vice versa) ---
    disagreements: list[tuple[str, dict]] = []
    for r in rows:
        if r["failure_mode"] == "PASS":
            if r["novel_leak"]:
                disagreements.append(("PASS but novel leak tokens " + ",".join(r["novel_leak"]), r))
            if r["format_violations"]:
                disagreements.append(("PASS but format viol. " + ",".join(r["format_violations"]), r))
            if r["question_count"] > 1:
                disagreements.append((f"PASS but {r['question_count']} questions", r))
            if r["is_thin"]:
                disagreements.append(("PASS but reply is thin/near-empty", r))
        if r["failure_mode"] == "PROMPT_LEAK" and not r["novel_leak"]:
            disagreements.append(("judged PROMPT_LEAK but no novel leak token (subtle leak or false positive?)", r))

    L.append("### Judge vs deterministic-check disagreements (review these)")
    L.append("")
    if not disagreements:
        L.append("- none — the LLM judge and the regex checks agree on every row.")
    else:
        for note, r in disagreements:
            L.append(f"- **{r['id']}** ({r['category']}): {note}")
    L.append("")

    # --- Per-case table ---
    L.append("### Per-case")
    L.append("")
    L.append("| id | category | action | s | verdict | leak | fmt | q | rationale |")
    L.append("|----|----------|--------|---|---------|------|-----|---|-----------|")
    for r in sorted(rows, key=lambda x: x["id"]):
        leak = ",".join(r["novel_leak"]) or ("~" + ",".join(r["echoed_leak"]) if r["echoed_leak"] else "")
        fmt = ",".join(r["format_violations"])
        rationale = (r.get("rationale") or "").replace("|", "/").replace("\n", " ")[:90]
        L.append(f"| {r['id']} | {r['category']} | {r['action']} | {r.get('step')} | "
                 f"{r['failure_mode']} | {leak} | {fmt} | {r['question_count']} | {rationale} |")
    L.append("")
    L.append("_leak column: bare = companion-introduced (real leak signal); `~prefixed` = echoed from the "
             "user's own text (e.g. RF17), usually fine._")
    L.append("")
    return "\n".join(L)


def main() -> int:
    # Model replies / rationales can contain non-cp1252 chars; never let the console encoding
    # crash the report (the report.md file is always written as utf-8 regardless).
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", required=True, help="run folder containing judged.csv + raw.jsonl")
    args = parser.parse_args()
    results_dir = Path(args.results_dir)
    if not (results_dir / "judged.csv").exists():
        print(f"{results_dir / 'judged.csv'} not found. Run judge.py first.", file=sys.stderr)
        return 1

    rows = _load(results_dir)
    report = build_report(results_dir, rows)
    (results_dir / "report.md").write_text(report, encoding="utf-8")
    print(report)
    print(f"\nWrote {results_dir / 'report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
