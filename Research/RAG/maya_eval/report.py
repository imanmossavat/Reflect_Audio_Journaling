"""Summarize results/judged.csv into per-failure-mode counts and the
'these questions go wrong and in this sense' table the user asked for.

Writes results/summary.csv and prints a readable table.

Run: python report.py
"""
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
JUDGED_CSV = HERE / "results" / "judged.csv"
SUMMARY_CSV = HERE / "results" / "summary.csv"


def main() -> int:
    if not JUDGED_CSV.exists():
        print(f"{JUDGED_CSV} not found. Run judge.py first.", file=sys.stderr)
        return 1

    rows = list(csv.DictReader(JUDGED_CSV.open(encoding="utf-8")))
    counts = Counter(r["failure_mode"] for r in rows)
    by_mode: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_mode[r["failure_mode"]].append(r)

    total = len(rows)
    print()
    print("=" * 72)
    print(f"Maya RAG eval — {total} questions")
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
        rationale = (r.get("rationale") or "")[:100]
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

    with SUMMARY_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["failure_mode", "count", "percent"])
        for mode, n in counts.most_common():
            writer.writerow([mode, n, f"{n*100/total:.1f}"])

    print(f"\nWrote summary to {SUMMARY_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
