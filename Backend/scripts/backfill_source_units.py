#!/usr/bin/env python
"""One-time backfill: compute Contract §8 units for sources ingested before
the per-unit addressing scheme existed (Phase 3), and index them into Chroma
for unit-level retrieval. Idempotent — safe to re-run; by default skips
sources that already have `units` set.

Usage:
    uv run python scripts/backfill_source_units.py            # skip already-backfilled
    uv run python scripts/backfill_source_units.py --force    # recompute + reindex all
    uv run python scripts/backfill_source_units.py --dry-run  # report counts, write nothing
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select  # noqa: E402

from app.db import engine  # noqa: E402
from app.repositories import sourceRepository  # noqa: E402
from app.services.retrieval import index_units  # noqa: E402
from app.services.units import compute_units  # noqa: E402
from database.models import Source  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Recompute and reindex sources that already have units")
    parser.add_argument("--dry-run", action="store_true", help="Report what would happen; write nothing")
    args = parser.parse_args()

    with Session(engine) as session:
        sources = session.exec(select(Source).where(Source.text.is_not(None))).all()

    todo = [s for s in sources if args.force or not s.units]
    print(f"{len(sources)} source(s) with text, {len(todo)} to backfill"
          f"{' (--force: recomputing all)' if args.force else ''}.")

    if args.dry_run:
        for s in todo:
            units = compute_units(s.text, s.transcript_segments)
            print(f"  source {s.id}: would compute {len(units)} unit(s)")
        return

    ok, failed = 0, 0
    for s in todo:
        units = compute_units(s.text, s.transcript_segments)
        try:
            with Session(engine) as session:
                source = sourceRepository.get_source_by_id(session, s.id)
                if source is None:
                    continue
                sourceRepository.update_source_units(session, source, units)
            index_units(str(s.id), units)
            ok += 1
            print(f"  source {s.id}: {len(units)} unit(s) backfilled")
        except Exception as exc:
            failed += 1
            print(f"  source {s.id}: FAILED — {exc}")

    print(f"Done. {ok} succeeded, {failed} failed.")


if __name__ == "__main__":
    main()
