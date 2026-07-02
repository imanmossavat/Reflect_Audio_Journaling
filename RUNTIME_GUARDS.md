# REFLECT — Runtime Safety Hooks

Surgical, non-invasive assertions that could be added at existing call
sites without redesigning anything. No new subsystem, no distributed
locking, no framework change. Each closes one specific silent-corruption
path identified in `ENFORCEMENT_MAP.md`.

| Hook | Category | Protects | Placement |
|---|---|---|---|
| Every node returned by a unit-scoped or chunk-scoped retrieval call must carry Chroma metadata matching that scope. | Must include filter X | R4 | Return boundary of `retrieval.py`'s query functions |
| A `reflection_state` write must be for the same `chat_id` that was read earlier in the same request/task. | Write must follow read in same context | R1 (partial — a sanity net, not a fix for the race itself) | Entry to `reflectionStateService.save_state` |
| Any exception inside a safety-classification call must resolve to the "safe" verdict before returning — never a "block" verdict paired with an exception. | Must never silently invert a default | R12 | Around `safety.classify_user_text` / `classify_ai_text` |
| `Source.status` must only advance through its known forward sequence — never jump backward, never skip to `processed` without passing through the intermediate statuses. | State transition must be monotonic | R6 (practical proxy) | Wherever `Source.status` is assigned |
| Immediately after a source-vector delete, a fresh Chroma count for that `source_id` must be zero before the delete is considered complete. | Post-condition must hold | R5 | End of the delete path in `sourceService.py` / `chroma.py` |
| Every generation job must emit exactly one terminal SSE event (`done` / `error` / `fallback` / `guard_unavailable`) before eviction — never zero, never more than one. | Must never silently omit a required signal | R7 | `generation_registry.py` job lifecycle |
| A write to `derived_meta` must be a superset of the previously-existing top-level keys, except the one key intentionally being replaced. | Must never clobber sibling state | R9 (defense in depth — already tested, this is a second layer) | Wherever `derived_meta` is written |

## What these hooks are, and are not

- These are **detectors**, not fixes. Several (R1, R6, R7) point at
  invariants whose real fix requires a design decision explicitly out of
  scope here (a per-chat lock, a durability layer, a structural session
  constraint). The hook only makes the violation loud instead of silent.
- None of these require a new dependency, a new table, or a new service.
  Each is a conditional check at a point the code already passes through.
- Where a hook would fire in production and not just in tests (e.g. the
  monotonic-status check, the delete post-condition), prefer logging the
  violation over raising — raising mid-pipeline could turn a detectable
  data problem into a worse availability problem. Let `ENFORCEMENT_MAP.md`'s
  "logging invariant" rows absorb these; only the retrieval-filter and
  fail-open hooks are safe to hard-assert, since both fire before any
  user-facing side effect has occurred.
