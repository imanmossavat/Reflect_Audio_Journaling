# REFLECT — Invariant Enforcement Strategy Map

For each P0/P1 invariant in `INVARIANTS.md`: detection mechanism type,
where it lives, the signal that indicates a violation, and how
detectable it is *today*. Priority is inherited from `INVARIANTS.md` —
not restated here. Emphasis throughout is on **silent** failure modes:
ones that produce no exception, no failed test, no error log.

| ID | Mechanism type | Lives in | Violation signal | Detectable today |
|----|---|---|---|---|
| R1 — `reflection_state` race | Concurrency test + logging invariant (write provenance/ordering log) | Backend: `reflectionStateRepository` | Two writes to the same `chat_id` where the second's pre-write state doesn't match the first's post-write state | **Impossible** — no write-provenance logging exists, no version field, nothing to compare against after the fact |
| R2 — reply must survive persistence failure | Unit test (per call site) + logging invariant (a distinct "reply delivered, state save failed" log class) | Backend: `reflectionLoop`, `generation_registry`, `routes/query.py` | An "error" reported to the client whose logs show a successful generation immediately upstream | **Easy** at 2 of 3 call sites (tested); **medium** at the route-level site (needs `TestClient`) |
| R3 — `generation_lock` scope | Architectural guard (static call-site inventory check) + concurrency test | Backend + infra (a repo-level check script) | A new `ollama.chat`/`classify_*` call site added without appearing in the lock-coverage inventory | **Medium** — mechanically checkable via a grep/AST pass; nothing does this today |
| R4 — unit/chunk filter | Unit test (both directions) + runtime assertion on result metadata | Backend: `retrieval.py` | A returned node whose Chroma `kind` metadata doesn't match the query's requested scope | **Easy** — cheap to add, currently absent |
| R5 — SQL+Chroma paired delete | Integration test + runtime post-condition assertion + logging invariant (log delete counts from both sides, flag mismatch) | Backend: `sourceService.py`, `chroma.py` | SQL delete succeeds but a follow-up Chroma count query for the same `source_id` is nonzero | **Medium** — this already happened once and was found by symptom, not by any detector; a post-condition check would close it |
| R6 — no shared ingestion transaction | Architectural guard only (structural/review constraint, not a data check) | Backend: `sourceService.py` (review-gated, not test-gated) | A session object referenced across more than one pipeline-stage function, or held open across a long call | **Impossible** to catch as a runtime/data test — it's a structural property; a static check or review rule is the only realistic detector |
| R7 — SSE state not durable | Integration test (clear registry mid-stream) + logging invariant (log every job create/complete) + runtime assertion (reconnect with no job always emits `idle`, never hangs) | Backend: `generation_registry.py`; Frontend: `GenerationProvider` | A reconnect request that neither replays a job nor emits `idle` | **Medium** — reproducible by directly clearing the in-memory registry in a test; nothing does this today |
| R8 — provenance staleness | Already pinned via `xfail(strict=True)` (detects a *fix*, not new violations); ongoing enforcement would need a logging invariant (flag every `derived_meta` write that follows a manual edit) | Backend: `sourceRepository.py` | A `derived_meta` generation timestamp that predates a later human edit to the same field, with no edit event recorded to compare against | **Impossible** today — no edit-vs-generation timeline exists to compare |
| R9 — `derived_meta` merge safety | Unit test (existing) | Backend: repository layer | A write that drops a sibling artifact's key | **Easy** — already tested |
| R10 — tag origin clearing | Unit test (existing) | Backend: repository layer | A clear operation that removes `origin="user"` rows | **Easy** — already tested |
| R11 — route-layer blindness | Integration test (`TestClient`) | Backend: `routes/query.py`, `routes/chat.py`, `routes/source.py` | Any route behavior change (status code, SSE shape, session handling) ships with nothing asserting prior behavior | **Impossible today, easy to build** — zero `TestClient` infrastructure exists yet; the pattern itself is standard for FastAPI |
| R12 — guard fails open on every error mode | Unit test (enumerate error modes) + architectural guard (a single wrapping pattern that structurally guarantees "exception → safe verdict" instead of relying on each function to remember it) | Backend: `safety.py` | A "block" verdict correlated with an exception in the logs, or any new `classify_*`-style function that doesn't route through the shared fail-open wrapper | **Easy** — cheap to enforce structurally, not yet done |

## Reading this map

- Every row marked **impossible** today (R1, R6, R8) shares one root
  cause: there is no write-provenance or state-transition logging
  anywhere in the system. This is the single highest-leverage gap — one
  logging convention would move three separate "impossible" rows to at
  least "detectable after the fact."
- Rows marked **easy** but currently absent (R4, R12) are the cheapest
  wins: no new infrastructure required, just an assertion at an existing
  call site.
