"""Summarize a run's judged.csv into per-failure-mode counts and the
'these questions go wrong and in this sense' table.

Input:  <results-dir>/judged.csv
Output: <results-dir>/failure_modes.csv  (+ printed table)

Run: python harness/report.py --results-dir runs/baseline/<ts>_<hash>
"""
import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", required=True, help="run folder containing judged.csv")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    judged_csv = results_dir / "judged.csv"
    summary_csv = results_dir / "failure_modes.csv"
    if not judged_csv.exists():
        print(f"{judged_csv} not found. Run judge.py first.", file=sys.stderr)
        return 1

    rows = list(csv.DictReader(judged_csv.open(encoding="utf-8")))
    counts = Counter(r["failure_mode"] for r in rows)
    by_mode: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_mode[r["failure_mode"]].append(r)

    total = len(rows)
    print()
    print("=" * 72)
    print(f"RAG eval — {total} questions  ({results_dir.name})")
    print("=" * 72)
    print(f"{'failure_mode':<30s} {'count':>5s}  {'%':>5s}")
    print("-" * 72)
    for mode, n in counts.most_common():
        print(f"{mode:<30s} {n:>5d}  {n*100/total:>4.0f}%")
    print()

    print("=" * 72)
    print("Per-question failure modes")
    print("=" * 72)
    for r in rows:
        rationale = (r.get("rationale") or "")
        print(f"{r['id']:>4s}  {r['failure_mode']:<25s}  {rationale}")
    print()

    print("=" * 72)
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
