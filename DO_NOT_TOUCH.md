# REFLECT — Architectural Immunity Layer

Explicit forbidden refactors and forbidden assumptions. If a change you
are making matches an item below, stop and get an explicit design
decision first — do not proceed on the assumption that it's obviously
correct cleanup.

## Forbidden refactors

- Merging the RAG-chat and reflection-loop prompts, personas, or
  retrieval paths into one.
- Wrapping multiple ingestion pipeline steps (transcription, chunking,
  indexing) in a single shared DB session or transaction.
- Removing or bypassing the unit/chunk metadata-tag filter, or merging
  the two Chroma "kinds" into one undifferentiated query.
- Flipping the safety guard from fail-open to fail-closed, under any
  framing ("safer default," "strict mode," "defense in depth").
- Adding stage-sequence enforcement to the reflection loop — no
  keyword-matched completion checks, no forced ordering, no server-side
  "must answer stage N before N+1." This was deliberately removed once;
  reintroducing it in any form is a regression, not a fix.
- Normalizing `reflection_state` into a full event-sourced/append-only
  log without a separate, explicit design decision. Today it is a single
  mutable row, last-write-wins, and other code assumes that shape.
- Consolidating the three independent device-availability checks
  (shell/`settings_service`/routes) into one shared implementation. The
  shell-level check runs before Python or torch exist and structurally
  cannot call into the others.
- Renaming or renumbering issues in the issue log without updating every
  code comment and test `xfail` reason that references them by number.
- Adding authentication, session, or single-active-user assumptions
  anywhere without an explicit design decision. The system currently
  assumes none of these, and `reflection_state` is exposed to concurrent
  multi-device access with no protection — code must not silently assume
  otherwise.
- Wrapping `generation_lock` around `reflection_state` persistence and
  treating that as sufficient concurrency protection. It is not — the
  lock only covers Ollama calls (see `INVARIANTS.md` R1, R3). Doing this
  creates a false sense of safety without fixing the underlying gap.

## Forbidden assumptions

- SQL and the vector store are interchangeable, or either can be fully
  reconstructed from the other without re-running embedding calls.
- A source's `processed` status implies every downstream artifact
  (units, tags, provenance) is populated for it.
- `derived_meta` is a reliable, current record of how content was
  produced. It goes stale after manual edits (confirmed, tracked in
  `INVARIANTS.md` R8) — do not build a trust-facing feature on it as-is.
- Deleting a row cleans up its dependents. No cascade rules exist in this
  schema (see `Backend/database/CLAUDE.md`).
- `ChatMessage.role` follows conventional `user`/`assistant` semantics.
  It does not — `"question"` means the AI spoke.
- Fields or pipelines that look unused are dead code. Some are
  intentionally inert (legacy request fields, the unused tag-extraction
  path) rather than accidentally unused — confirm zero callers *and*
  check whether removing them is itself listed above before deleting.

## Escalation rule

If a task requires violating one of the above to proceed, treat that as
a signal to stop and surface the conflict explicitly rather than choosing
a workaround — these constraints were each established after a concrete,
previously-observed failure or a deliberate, considered tradeoff, not by
default caution.
