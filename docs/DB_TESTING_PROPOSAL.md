# Repository-level DB tests

> **Status: implemented** (2026-07-01). Originally a proposal; now built at
> `Backend/tests/repositories/`. This doc records the reasoning so the
> "why" stays attached to the tests, the same way other docs in this repo
> do. Revised from the original proposal in three ways — see "What changed
> from the original proposal" at the bottom.

## Problem

Every existing test mocks `sourceRepository` (or `sourceService`) rather than
hitting a real database, so repository logic itself was never verified. Two
functions in particular have non-trivial merge behavior:

- `update_source_summary` — merges `{"summary": ...}` into `Source.derived_meta`
  without clobbering other keys.
- `update_source_transcript` — same pattern, merges `{"transcript": ...}`
  (added July 2026 alongside transcription metadata).

A bug in that merge (e.g. `source.derived_meta = provenance` instead of
`meta["transcript"] = provenance; source.derived_meta = meta`) would silently
wipe out the other artifact's provenance and no test would catch it.

Separately, tags, summaries, and transcripts are being retrofitted onto a
shared provenance shape in one pass (see Document B's build order) precisely
because they're the same kind of risk. Their repository write paths belong
in this same batch of tests, not staggered across separate sessions.

## Implementation

`Backend/tests/repositories/conftest.py` provides two fixtures:

- **`session`** — schema built directly from the current SQLModel classes via
  `create_all()`. Fast, fully isolated per test. Used for repository *logic*
  tests (merges, filters, provenance writes).
- **`migrated_session`** — schema produced by actually running the real
  Alembic migration chain against a throwaway on-disk SQLite file (once per
  test session, wrapped per-test in a rolled-back transaction). Used for
  the one thing `create_all()` structurally can't catch: drift between what
  a migration actually produces and what the ORM model expects.

Three test files:

- **`test_source_provenance.py`** — the two merge tests from the original
  proposal, plus two `xfail(strict=True)` tests for the real confirmed bug
  (docs/ISSUES.md #12): editing summary/transcript text through the normal
  manual-edit path (`update_source_fields`) never touches `derived_meta`, so
  the stamp keeps claiming the original AI generation as if untouched.
  `strict=True` means these flip from `XFAIL` to a hard failure the moment
  someone fixes #12 — forcing the fix to come with an updated test, not
  silently pass.
- **`test_tag_provenance.py`** — `add_tag_to_source`'s origin defaulting,
  `clear_llm_tags_for_source`'s filter logic (must remove only
  `origin="llm"` links and preserve `"user"` ones — the tag-side equivalent
  of the merge-clobber risk above), and a pinned (non-xfail) test recording
  today's known limitation (docs/ISSUES.md #15): a confirmed LLM suggestion
  is persisted identically to a hand-typed tag, so that history is already
  unrecoverable. No xfail here because there's no confirmed "correct" shape
  yet to assert toward — that's the upcoming provenance work's decision to
  make, not something to presume in a test today.
- **`test_migration_drift.py`** — round-trip writes through `migrated_session`
  for the four columns `alembic check` already flagged as drifted
  (`chat_message.thinking`, `source.text_html`, `source.summary`,
  `source.summary_html` — docs/ISSUES.md #17), plus a sanity check that the
  migrated engine actually ran the full chain (checks for `source_tag.origin`,
  which only a real migration adds). A functional round-trip, not a strict
  type-equality assertion, because the existing drift is harmless on SQLite
  (TEXT/VARCHAR-without-length are storage-identical there) — the point is
  to catch a *future* migration drifting in a way that actually breaks
  storage, which the provenance retrofit's new migration is a live
  candidate for.

Verified two ways beyond "tests pass": (1) confirmed the real dev
`database/database.db` is never touched by `migrated_engine` (checksum
identical before/after — the fixture swaps `app.db.engine` for the
migration only, since `migrations/env.py` imports it directly and ignores
`alembic.ini`'s configured URL); (2) confirmed the `xfail(strict=True)`
tests actually catch a fix by temporarily patching `update_source_fields`
to touch `derived_meta`, rerunning, and observing `XPASS(strict)` hard
failures as expected, then reverting.

## Scope

Not backfilled to every repository function — matches the original
proposal's restraint, just widened to match what's moving together. Add
more repository tests opportunistically when touching that code, the same
way service-level tests already exist for `sourceService`.

## What changed from the original proposal

1. **Scope widened to include the tag-provenance write path.** The original
   proposal scoped itself to the two `derived_meta` functions. Since tags,
   summaries, and transcripts are being retrofitted together specifically
   because they're the same risk, their repository tests were added in the
   same pass rather than left for later.
2. **The real bug replaced the hypothetical one as the primary test case.**
   The original example tested a *hypothetical* clobber risk (one write
   overwriting another's key). That's still tested, but the audit
   confirmed a different, real bug — the stale-stamp-after-manual-edit
   issue (#12) — which now has its own `xfail(strict=True)` tests specifically
   because it's a confirmed defect, not a hypothetical one.
3. **The migration-drift question is resolved, not deferred.** The original
   "open question" suggested revisiting on-disk migrated SQLite "if that gap
   matters later." It already does: `alembic check` confirmed real drift
   exists right now (docs/ISSUES.md #17), and the provenance retrofit is
   about to add a migration of exactly the kind that could drift the same
   way. `migrated_session` and `test_migration_drift.py` are built now, not
   promised for later.
