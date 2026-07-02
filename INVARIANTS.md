# REFLECT — Invariant → Test Mapping

Structured detection map for the constraints in `CLAUDE.md`. Each entry:
what breaks, how it should be detected, priority, current test status.
This document does not contain test code — only detection strategy.

| ID | Invariant | What breaks if violated | Detection strategy | Priority | Status |
|----|---|---|---|---|---|
| R1 | `reflection_state` writes have no per-chat lock | Silent lost update — Gist/Open Thread reverts with no error, no log a user would see | Concurrency/integration test: fire two overlapping turn requests at the same `chat_id`, assert either serialized ordering or a detectable conflict — not silent overwrite | P0 | **Untested** — no concurrency tests exist in the suite |
| R2 | Generation success must survive a downstream persistence failure | An already-generated, already-shown-worthy reply gets reported as failed/lost | Unit test per call site: inject a persistence failure after successful generation, assert reply is still returned and only the persistence error is logged | P0 | **Partial** — covered in `reflectionLoop.run_update` and the RAG post-turn hook; route-level (`/generate-question`) save path has no test |
| R3 | `generation_lock` does not serialize safety-guard calls or DB writes, only Ollama generation calls | Under concurrent chats, guard and main-generation calls can run simultaneously (VRAM/model contention); state writes race independent of the lock | Static/structural check: enumerate every `ollama.chat`/`classify_*` call site and confirm lock coverage matches documented scope; integration test asserting call serialization under concurrent load | P1 | **Untested** |
| R4 | Unit vs. chunk retrieval filter must always be applied | Retrieval silently mixes granularities — degraded or mismatched context/citations, no error | Unit test at the retrieval boundary: assert unit-scoped queries return only unit-tagged vectors and chunk queries exclude them (both directions, not just the positive case) | P0 | **Partial** — positive-path coverage exists (`test_unit_retrieval.py`, `test_units.py`); negative-path (chunk query excludes units) not confirmed |
| R5 | SQL chunk deletion and Chroma vector deletion must stay paired on reprocess/delete | Orphaned, stale, still-searchable vectors after reprocess (previously happened once) | Integration test: reprocess/delete a source, assert both SQL rows and matching Chroma vectors are gone | P0 | **Indirect only** — covered incidentally by `test_journalService.py` reprocess cases; no dedicated regression test |
| R6 | Ingestion pipeline steps must not share one DB session/transaction | Reintroduces SQLite write-lock contention across the whole app during transcription/LLM calls | Not independently unit-testable; enforce via code review checklist (flag any session held open across an `await`/long call) rather than a runtime test | P1 | **Not testable in the conventional sense** — review-gate only |
| R7 | SSE job state is not durable across a process restart | Backend restart mid-generation silently loses the job; client cannot distinguish "done" from "forgotten" | Integration test: simulate registry loss mid-stream (clear job state), assert client reconnect path resolves to a well-defined state (e.g. `idle`) rather than hanging or erroring ambiguously | P1 | **Untested** |
| R8 | `derived_meta` provenance stamp must reflect the true origin of current content, including after manual edits | Displayed/trusted provenance misrepresents human-edited content as untouched AI output | Currently pinned via `xfail(strict=True)` — detects when someone *fixes* the behavior, not a regression detector for new violations | P1 (P0 if provenance ever becomes a user-facing trust signal) | **Confirmed broken, tracked** — not "passing," intentionally pinned |
| R9 | `derived_meta` JSON merges must not clobber sibling keys across independent writers | One artifact's provenance write silently erases another's (e.g. tag provenance wipes summary provenance) | Unit test at the repository layer: write summary provenance, then transcript/tag provenance, assert all keys survive | P0 | **Tested** |
| R10 | Tag `origin` clearing must remove only `origin="llm"` rows | A recompute/re-extraction silently deletes user-added tags | Unit test: seed both origins, run clear, assert only `llm`-origin rows removed | P0 | **Tested** |
| R11 | Route-layer behavior (`/generate-question`, `/query-stream`, `/chats/{id}/generation-stream`) | Regressions in request parsing, session lifecycle, or SSE event framing ship undetected — this is how the last batch of bugs actually surfaced (live, not via tests) | `TestClient`-based route tests: assert status codes, SSE event shape/ordering, and error-path behavior per endpoint | P0 | **Untested** — zero `TestClient` usage anywhere in the suite |
| R12 | Fail-open must hold under every guard error mode (missing model, timeout, malformed response) | An inverted fail-closed path blocks journaling entirely on a transient local Ollama failure | Unit test per error mode: force each failure type, assert verdict is always non-blocking | P0 | **Partial** — some guard behavior tested (`test_safety.py`); "every error mode fails open" not confirmed as one enumerated property |

## Reading this table

- **P0** = correctness or safety property; a violation is silent and
  user-facing or trust-facing.
- **P1** = reliability/perf property; a violation degrades the system but
  is more likely to be noticed operationally.
- "Untested" does not mean "unimportant" — several P0 rows are untested
  specifically because they require concurrency or process-restart
  scenarios the current suite has no infrastructure for.
