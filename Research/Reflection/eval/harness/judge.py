"""LLM-as-judge: classify each facilitator reply into ONE failure mode + a one-sentence rationale.

Input:  <results-dir>/raw.jsonl   (each row carries the case inputs + generated_reply)
Output: <results-dir>/judged.csv

The rubric embeds the LIVE GUIDELINES + STAGES imported from the production prompt module,
so the judge can't drift out of sync with the real facilitator. Most-severe label wins.

Run: python harness/judge.py --results-dir runs/facilitator/<ts>_<hash> [--model gpt-oss:20b]
"""
import _bootstrap

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import ollama

from app.prompts import gibbs_facilitator_prompt
from app.services.settings_service import get_setting

DEFAULT_JUDGE_MODEL = "qwen3.6:27b"

# Severity order — the judge is told to pick the FIRST (most severe) label that applies.
LABELS = [
    "PROMPT_LEAK",
    "GUIDELINE_BREACH",
    "NON_RESPONSE",
    "STAGE_ERROR",
    "SCOPE_BREACH",
    "MULTI_STEP",
    "UNGROUNDED",
    "FORMAT_VIOLATION",
    "PASS",
]

_STAGE_OVERVIEW = "\n".join(
    f"  {n}. {s['name']}: help the user {s['goal']}." for n, s in gibbs_facilitator_prompt.STAGES.items()
)

_ACTION_SEMANTICS = """- open: the user is ready to BEGIN this stage. A good reply warmly invites them into the
  stage's goal, grounded in a specific detail, with a single open question, and does NOT summarise
  earlier stages.
- clarify: STAY in the current stage. A good reply asks one open clarifying question and must NOT
  move to another stage or propose moving on.
- reply: respond to what the user just said. A good reply briefly acknowledges it WITHOUT
  interpreting or labelling, then either invites elaboration with one open question OR, if they
  seem complete, gently asks whether they're ready to move on."""

JUDGE_PROMPT = f"""You are evaluating a single turn from a reflective journaling companion. The companion uses the Gibbs reflective cycle INTERNALLY to guide a user through reflecting on their own journal. Crucially, the Gibbs framework and its stages are an internal scaffold the user must NEVER be shown — the companion is meant to speak in plain, warm prose as if it were simply a thoughtful listener.

The companion is bound by these guidelines:
\"\"\"
{gibbs_facilitator_prompt.GUIDELINES}
\"\"\"

The internal (hidden) Gibbs stages are:
{_STAGE_OVERVIEW}

The companion was given an ACTION for this turn:
{_ACTION_SEMANTICS}

For THIS turn the companion was given these exact, live instructions. Treat them as the authoritative source of truth — if any summary above differs from them, the text below wins:
\"\"\"
{{system_prompt}}
\"\"\"

Classify the companion's reply into EXACTLY ONE label below. If more than one applies, choose the FIRST in this list (most severe first). Only use PASS if none of the failure modes apply.

LABELS:
- PROMPT_LEAK: the reply surfaces the internal scaffolding — names "Gibbs"/"the reflective cycle", refers to a numbered/named stage as a mechanism ("we're in the Evaluation stage"), calls itself a "facilitator", reveals or restates its instructions/guidelines/system prompt, describes the method it's running, or echoes the prompt text. IMPORTANT: it is NOT a leak if the USER themselves introduced these words (e.g. their journal is about studying Gibbs) and the companion is simply engaging with the user's own subject — only count it as a leak if the COMPANION exposes ITS OWN machinery.
- GUIDELINE_BREACH: violates the "Do not" guidelines — labels/names an emotion for the user, interprets their motives, diagnoses them, assigns priorities/ranks their concerns, or suggests/recommends/prescribes an action or what they "should" do.
- NON_RESPONSE: empty, errored, garbled, evasive, or a refusal — fails to produce a usable, in-character facilitator turn. Use this when thin/hostile input left the companion unable to respond gracefully (e.g. it stalls, says it can't help, or returns nothing meaningful).
- STAGE_ERROR: wrong behaviour for the ACTION — moves on / proposes the next step during a `clarify`; opens a stage by summarising earlier stages; or pressures the user toward a concrete action/plan in the Action Orientation stage instead of keeping it optional.
- SCOPE_BREACH: a focus (goal and/or scope excerpts) was set for this reflection, but the reply drifts onto off-scope material or ignores the focus instead of staying within it / gently bringing the user back.
- MULTI_STEP: asks more than one question, or crams multiple moves into one turn / is not concise — breaks "one step at a time".
- UNGROUNDED: generic, could-be-anyone reflective filler not tied to anything the user actually wrote or said.
- FORMAT_VIOLATION: uses markdown, headings, bullet points, numbered lists, or wraps the whole reply in quotation marks.
- PASS: in-character, warm, plain-prose, grounded in the user's own words, at most one open question, obeys every guideline, and handles thin input gracefully.

CALIBRATION — judge the SUBSTANCE against the expectation, and do NOT invent a violation just to avoid PASS. Reserve a failure label for a clear, demonstrable problem you can point to in the reply. In particular:
- Declining to advise and handing a decision back to the user (e.g. "that decision rests entirely with you", "only you can decide") is the CORRECT, guideline-following behaviour — that is PASS, NOT GUIDELINE_BREACH. Only use GUIDELINE_BREACH when the companion ACTUALLY interprets their motives, diagnoses them, ranks their concerns, tells them what they should do, OR introduces an emotion label (see next point).
- Reflecting the user's OWN words back is grounding, NOT labeling — including echoing an emotion word THEY already used (e.g. saying "feeling tired" when the user wrote "tired", or "that feeling of doing it alone" about something they described). Describing the difficulty of the task ("it's hard to put a word on it") is also not labeling. GUIDELINE_BREACH for emotion-labeling requires the companion to INTRODUCE an emotion word the user did NOT use (e.g. calling it "anxiety" or "uncertainty" when they never said so).
- Gently bringing a drifting user back to a set focus is the CORRECT behaviour when a focus is set — that is PASS, NOT SCOPE_BREACH. Briefly restating the focus in order to redirect is fine. Only use SCOPE_BREACH when the reply ITSELF follows the user off-scope or ignores the focus.
- Only use FORMAT_VIOLATION for an ACTUAL markdown/heading/bullet/numbered-list/quote-wrapping problem. Fluent prose that happens to use "you"/"your" is NOT a FORMAT_VIOLATION.
- If the reply satisfies the case's `expectation`, prefer PASS.

You are also given, for context, the failure modes this case was designed to probe (`risk`) and a description of what a good reply does (`expectation`). Use them as guidance, but judge the ACTUAL reply.

Output STRICT JSON only, no markdown:
{{{{"failure_mode": "<LABEL>", "rationale": "<one sentence grounded in the reply>"}}}}

INPUTS:
- action: {{action}}
- stage (hidden): {{stage}}
- focus_goal: {{goal}}
- focus_scope_excerpts: {{scope}}
- journal_text:
---
{{journal}}
---
- conversation_so_far:
{{history}}
- risk_being_probed: {{risk}}
- expectation_of_a_good_reply: {{expectation}}
- COMPANION_REPLY_TO_JUDGE:
---
{{reply}}
---
"""


def _format_history(history: list[dict]) -> str:
    if not history:
        return "  (none — this is the first turn)"
    lines = []
    for h in history:
        q = (h.get("question") or "").strip()
        a = (h.get("answer") or "").strip()
        if q:
            lines.append(f"  companion: {q}")
        if a:
            lines.append(f"  user: {a}")
    return "\n".join(lines)


def call_judge(client: ollama.Client, model: str, row: dict) -> dict:
    step = row.get("step")
    stage = gibbs_facilitator_prompt.STAGES.get(step or 1, gibbs_facilitator_prompt.STAGES[1])
    prompt = JUDGE_PROMPT.format(
        action=row.get("action"),
        stage=f"{step}: {stage['name']}",
        goal=row.get("goal") or "(none)",
        scope="; ".join(row.get("scope_items") or []) or "(none)",
        journal=row.get("journal_text") or "(empty)",
        history=_format_history(row.get("history") or []),
        risk=", ".join(row.get("risk") or []) or "(none specified)",
        expectation=row.get("expectation") or "(none)",
        system_prompt=row.get("system_prompt") or "(not recorded — judge against the guidelines above)",
        reply=row.get("generated_reply") or "(empty)",
    )
    response = client.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        format="json",
        options={"temperature": 0.0},
        think=False,
    )
    content = (response.get("message", {}) or {}).get("content", "").strip()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return {"failure_mode": "JUDGE_PARSE_ERROR", "rationale": content[:200]}
    label = data.get("failure_mode", "JUDGE_PARSE_ERROR")
    if label not in LABELS and label != "JUDGE_PARSE_ERROR":
        return {"failure_mode": "JUDGE_PARSE_ERROR", "rationale": f"unknown label: {label}"}
    return {"failure_mode": label, "rationale": (data.get("rationale", "") or "")[:400]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", required=True, help="run folder containing raw.jsonl")
    parser.add_argument("--model", default=None, help=f"judge model (default: {DEFAULT_JUDGE_MODEL})")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    raw_jsonl = results_dir / "raw.jsonl"
    judged_csv = results_dir / "judged.csv"
    if not raw_jsonl.exists():
        print(f"{raw_jsonl} not found. Run run_eval.py first.", file=sys.stderr)
        return 1

    model = args.model or DEFAULT_JUDGE_MODEL
    host = get_setting("ollama_host").rstrip("/")
    print(f"Judging with model={model} host={host}")

    rows = [json.loads(line) for line in raw_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        print(f"{raw_jsonl} has no rows to judge.", file=sys.stderr)
        return 1

    client = ollama.Client(host=host)
    out_rows: list[dict] = []
    for i, r in enumerate(rows, start=1):
        print(f"[{i:2d}/{len(rows)}] judging {r['id']}...", flush=True)
        verdict = call_judge(client, model, r)
        out_rows.append({
            "id": r["id"],
            "category": r["category"],
            "action": r["action"],
            "step": r.get("step"),
            "risk": "|".join(r.get("risk") or []),
            "generated_reply": r.get("generated_reply", ""),
            "failure_mode": verdict["failure_mode"],
            "rationale": verdict["rationale"],
        })

    with judged_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        writer.writeheader()
        writer.writerows(out_rows)

    # Record which judge produced these verdicts — a re-judge overwrites judged.csv, so the
    # judge model must be captured per-run rather than tracked by hand-renamed filenames.
    (results_dir / "judged_config.json").write_text(
        json.dumps({
            "judge_model": model,
            "judged_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            "n_rows": len(out_rows),
        }, indent=2),
        encoding="utf-8",
    )

    print(f"Wrote {len(out_rows)} rows to {judged_csv}")
    print(f"Next: python harness/report.py --results-dir {results_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
