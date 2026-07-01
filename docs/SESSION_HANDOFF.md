# Session handoff — 2026-07-01 (reflection flow rebuild)

Working tree clean; everything below is committed (`8cd5f3c` Phase 0,
`b718aed` Phase 2a, `1f1a223` Phase 2b — Phase 1 landed inside the Phase 2b
commit). Full plan lives at `/Users/imanm/.claude/plans/lexical-spinning-kahn.md`
(local to this machine, not in the repo) — read that for the complete
phase-by-phase design; this file is just the status snapshot.

## Done

- **Phase 0 — provenance schema**: `Source.provenance` / `Source.verified`
  added, migration `b6d4e5f7a9c1`, written into
  `docs/REFLECT_Implementation_Contract.md` §2.1.
- **Phase 1 — `reflection_state` table + simplified `Focus`**: migration
  `c7e5f9a1b3d2`. `Focus.value` = the existing `Chat.reflection_goal` text
  as-is — no new mode-picker UI (deferred, pending an intern conversation).
- **Phase 2a — Ask/Update loop against mocks**: `app/services/reflectionLoop.py`
  (retrieve/Ask/thin-gate/Update, in-memory state, whole-source retrieval
  stub), `app/prompts/reflection_{ask,update}_prompt.py`. Manual iteration
  script: `Backend/scripts/run_reflection_turn.py`.
- **Phase 2b — real wiring**: `app/services/reflection_guard.py` (ported
  from the eval harness, verified against its real fixtures — stage-gated
  `state.py` was *not* ported, by design). Guard wired into `run_ask`
  (input short-circuit, output repair-then-fallback). `resolve_hint` feeds
  the "Answer & next" confirmation into Update as context, not a code
  override. `reflectionStateRepository`/`reflectionStateService` bridge the
  DB row and the loop's Pydantic state. `/generate-question` fully
  rewritten (four-lever aware: reflect/clarifying/deep_dive/reply modes,
  `chat_id` now required) — same SSE wire shape, so the frontend buttons
  needed no redesign. `generation_registry._run` now runs Update after an
  "Ask sources" RAG turn when the chat has a `reflection_state` row.
  Frontend: `chat_id` threaded through, `onReflect` now fires a background
  `mode: "reflect"` call. `tsc --noEmit` clean, 163 passed/2 xfailed.

## Not done yet

- **Phase 3** — real per-unit retrieval. Currently still Phase 2a's
  whole-source bridge (capped ~250 tokens). `ranked_retrieve`/Chroma infra
  already exists and is reusable; what's missing is stable per-unit
  citation ids (paragraph/WhisperX-segment), not the retrieval pipeline
  itself — see the plan file for detail.
- **Phase 4** — cleanup: delete `gibbs_facilitator_prompt.py` and the dead
  `mode: "reply"` path once Phase 3 is done.
- **Not yet run live** — no manual `/run` walkthrough against real Ollama
  yet. Everything is unit/repository-tested with mocked model calls; the
  actual four-button experience hasn't been eyeballed.

## Known deliberate simplification

Ask/Update now call Ollama non-streaming (guard's repair pass made
token-streaming meaningfully harder to fit into Phase 2b's scope), so the
frontend's progress skeleton will jump to done instead of animating. Wire
shape is unchanged — recoverable later without touching the contract.

## Deferred (recorded in Document A §10 and the plan file, not repeated here)

Provenance-scoped quoting / per-unit source selection UI, Focus mode-picker
UI, lighter opening-turn prompts, out-of-order stage navigation — all
pending either the intern conversation or later prompt-design work.
