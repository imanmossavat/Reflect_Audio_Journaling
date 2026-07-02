# Session handoff — 2026-07-01 (reflection flow rebuild)

**Phases 0, 1, 2a, 2b, 3, 4 are all done.** Plan lives at
`/Users/imanm/.claude/plans/lexical-spinning-kahn.md` (local to this
machine, not in the repo) for full design detail; this file is the status
snapshot.

**Working tree: mostly committed, one batch outstanding.** Phases 0/2a/2b
landed in commits `8cd5f3c`/`b718aed`/`1f1a223` (plus `20e58e7`, a
handoff-doc-only commit). Phase 3 + 4 landed in `41916d3`. The live-test
bugfixes (#18-#21, below) landed in `b2fd6b3`. The 2026-07-02 follow-up
(below) landed in `b87a39e` (docs) and `028701b` (prompt). The
2026-07-02 documentation-governance pass (further below) is **not yet
committed** — 7 new root files plus 3 local `CLAUDE.md` files, all
currently untracked.

**The real local dev database (`Backend/database/database.db`) was
migrated to head this session** (`alembic upgrade head`, applying
Phase 0/1/3's three new migrations) — it was still on last week's schema
before this. Reversible via `alembic downgrade` per-revision if needed.

## Done

- **Phase 0/1/2a/2b** — unchanged from before, see prior handoff content /
  git log messages. Provenance schema, `reflection_state` table +
  simplified `Focus`, the Ask/Update loop, the guard, and the four-lever
  route rewrite.
- **Phase 3 — real per-unit retrieval**:
  - `app/services/units.py` (`compute_units`) — paragraph-boundary units
    for typed entries, transcript-segment units for audio. Correction
    found while implementing: `Source.transcript_segments` has no
    carried-over WhisperX id, so unit ids are the list index, not a truly
    "already-existing" id as Document B originally assumed.
  - `Source.units` column (migration `d8f2a4c6b1e3`), hooked into
    `sourceService._process_source_sync` right after chunking.
  - `retrieval.index_units`/`retrieve_units`/`serialize_unit_nodes` — reuse
    the *same* Chroma collection chunks already use, separated at query
    time via a `"kind": "unit"` tag. Scoped by a `source_id` hard filter,
    **not** `chat_id`-in-metadata as Document B originally specified — a
    unit's embedding is intrinsic to its source, not any one chat; §8 is
    corrected with the reasoning.
  - `reflectionLoop.retrieve()` now calls real retrieval instead of the
    Phase 2a whole-source stub — Ask/Update code itself never changed.
  - `scripts/backfill_source_units.py` (idempotent, `--dry-run` tested
    against the real dev DB: 2 sources, 565 + 2 units).
  - **Bug caught and fixed along the way**: the units hook initially threw
    `AttributeError` inside `_process_source_sync`'s broad exception
    handler, silently swallowed — two pre-existing tests still went green
    because they only asserted on pipeline behavior *before* that point.
    Fixed with a defensive `getattr` plus tightened test assertions
    (`update_source_units`/`index_units` actually called, final status is
    `"processed"` not `"failed_*"`) so this class of silent failure can't
    hide again.
- **Phase 4 — cleanup**: `gibbs_facilitator_prompt.py` deleted;
  `Mode.reply` removed from `journalSchemas.py` (confirmed dead — the
  frontend never sent it). `Research/Reflection/eval/`'s harness still
  imports `gibbs_facilitator_prompt` in a few files — now broken by this
  deletion, but that harness is the explicitly-out-of-scope stage-gated
  dead end from Step 0, not something this rebuild maintains.

## Live-tested — found and fixed 4 bugs (docs/ISSUES.md #18-#21)

Ran live against real Ollama for the first time. Found: a checkbox-tick race
in the setup wizard (#18), a false-positive safety-card trigger from Llama
Guard's S6 category (#19), and — via self-review pattern-matching against
#18/#19, not live-reproduced — a 3-layer "Update failure discards an
already-successful Ask reply" bug spanning `reflectionLoop.run_update`,
the `/generate-question` route, and `generation_registry`'s post-RAG Update
hook (#20). All four fixed, with regression tests except the route-level
half of #20 (no TestClient precedent in this repo). #21 is a related,
unconfirmed watch item, not fixed — see ISSUES.md for why.

## Follow-up (2026-07-02) — Ask Sources confusion mid-flow

Live use surfaced a case that looked like a bug: using "Ask sources" in the
middle of a reflection produced a reply in a visibly different voice, with
no citations, plus a chain-of-thought (shown in the "Thoughts" panel) that
reasoned its way out of grounding on the journal at all. Two distinct
things came out of digging into it, one doc-only and one a real fix:

- **Doc gap, not a bug**: "Ask sources" is deliberately a side-channel, not
  part of the Ask/Update turn loop — it hits the older general RAG chat
  path (`generation_registry.py`'s `SYSTEM_PROMPT` + chunk-level
  retrieval), not the reflection facilitator's prompt/persona or Phase 3's
  per-unit retrieval. That was true by design but undocumented anywhere.
  Now written up in `docs/HANDOVER.md` under "The three input-area levers,
  and which are 'in the flow'" (commit `b87a39e`).
- **Real fix**: the leaked chain-of-thought showed the model bucketing a
  reflective personal question ("what boundary should I set for my
  future") under `SYSTEM_PROMPT`'s small-talk/meta-request branch, which
  let it skip grounding *and* the explicit refusal line, defaulting to
  generic coaching instead. Tightened that branch in
  `Backend/app/services/prompt.py` to scope it to literal small talk only,
  and made reflective/open-ended personal questions route into the
  grounding rules explicitly (commit `028701b`).
  - **Not yet done**: this `SYSTEM_PROMPT` is the same one the
    `Research/RAG/eval` harness tuned to lift stateful answer accuracy
    0.467 → 0.667 by cutting false refusals (see that harness's
    `FINDINGS.md`). This change pushes the opposite direction (more
    grounding attempts, less silent bypass) and hasn't been re-evaluated
    against that harness yet — do that before treating it as settled.

## Follow-up (2026-07-02, cont'd) — Repository Operating System / documentation governance layer

Separate from the reflection-flow rebuild above: a full pass at making the
system's implicit invariants and fragile areas explicit and (eventually)
enforceable, done through iterative review rather than code changes. No
production code touched in this pass — docs and root-level files only.

- **`CLAUDE.md`** (root) rewritten twice: first as a descriptive
  architecture/testing/invariants writeup (verified against the running
  code — caught `docs/HANDOVER.md` still describing the deleted
  `gibbs_facilitator_prompt.py` flow as current), then rewritten again
  into its current terse, constraint-only form once the doc's purpose
  shifted from "explain the system" to "bind future changes." The
  descriptive content from the first pass isn't lost — it's what informed
  every file below, it's just not restated in any of them (each file
  points back to Design Doc/Contract/this handoff for "why").
- **`INVARIANTS.md`** — 12 numbered invariants (R1-R12) covering
  concurrency, SSE lifecycle, ingestion consistency, provenance, and
  route-level coverage, each with a detection strategy, priority, and
  current test status. Two flagged P0 and fully untested: R1
  (`reflection_state` has no per-chat lock — two overlapping requests on
  the same `chat_id`, which the app's own LAN/mobile-upload support makes
  a real scenario, can silently lose an update) and R11 (zero
  `TestClient`/route-level tests exist anywhere in the repo — this is
  literally how #18-#21 above were actually found, live rather than by a
  test).
- **`DO_NOT_TOUCH.md`** — explicit forbidden-refactor list (don't merge
  RAG/reflection personas, don't fail-closed the safety guard, don't
  re-add stage gating, don't collapse the ingestion session-per-step
  pattern, etc.), each tied to a concrete prior incident or a deliberate,
  already-made tradeoff rather than default caution.
- **`ENFORCEMENT_MAP.md`**, **`TEST_STRATEGY.md`**, **`RUNTIME_GUARDS.md`**
  — a detection-mechanism map, an 8-test P0 blueprint, and 7 lightweight
  runtime-assertion proposals respectively. **All three are proposals,
  not implementations** — no test code and no runtime assertions were
  actually written this session.
- **`CHANGE_IMPACT_RULE.md`** — a 3-question pre-change self-check meant
  to bind future Claude sessions specifically, for the six highest-risk
  areas (reflection loop, ingestion, `generation_registry`, SSE,
  `reflection_state` schema, retrieval).
- **`HUMAN_PROCESS.md`** — the explicit, deliberately blunt admission that
  none of the above actually enforces anything yet: with `TEST_STRATEGY.md`
  and `RUNTIME_GUARDS.md` unimplemented, every P0 invariant in
  `INVARIANTS.md` can be violated today by an ordinary change and ship
  with zero warning. This file is the only layer that's binding right
  now, and only insofar as someone actually follows its short
  before/after change-justification format.
- **Local `CLAUDE.md` files** added at `Backend/app/services/`,
  `Frontend/hooks/`, and `Backend/database/` — layer-specific invariants
  and "what gets gotten wrong here" notes, deliberately not repeating the
  root file's content.

## Follow-up (2026-07-02, cont'd) — access-log noise from the poll loops

A code-review comment flagged that the three frontend poll loops documented
in `docs/ISSUES.md` #21 (`GET /chats` every 5s, `GET /sources` every 5s, `GET
/source/{id}` every 2.5s while a source is processing — each running
independently per open tab) were producing a constant stream of uvicorn
access-log lines at INFO level, on console and in `logs/app.log`. With more
than one tab open this is effectively continuous noise that buries real
signal during live debugging. Explicitly separate from #21 itself, which is
about a possible state-clobber bug in the poll's merge logic, not logging.

**Fix (`docs/ISSUES.md` #22), two parts**:

1. **Logging**: `Backend/app/logging_config.py` now attaches a
   `logging.Filter` to the `uvicorn.access` logger that drops successful
   (2xx) `GET` requests to the three polled routes only — every other route,
   every non-GET method, and every failing poll (a real signal) still logs
   exactly as before.
2. **Actual request volume**: the three `setInterval` loops in
   `useChatManagement.ts`/`useSourceManagement.ts` now skip their tick while
   `document.visibilityState === "hidden"`, with one immediate resync on
   `visibilitychange` back to visible. A backgrounded tab now makes zero
   polling requests instead of one every 2.5-5s — this was the more common
   case widening #21's race window than multiple simultaneously-*visible*
   tabs.

What gets logged, concretely, after this change: every non-polling route
(POST/PATCH/DELETE, SSE stream opens, uploads) at INFO as before; every
polling GET that fails or returns non-2xx (backend down, 4xx/5xx) at INFO as
before — a failing poll is real signal, not noise; every successful polling
GET (`/chats`, `/sources`, `/source/{id}`) is now silent in both console and
`logs/app.log`. `LOG_LEVEL=DEBUG` (the default) still shows everything else
this file's noisy-third-party-logger list doesn't already suppress.

**Not done**: two or more *simultaneously visible* tabs (e.g. side-by-side
windows) still each poll independently — no cross-tab leader election was
added. See `docs/ISSUES.md` #22's "Not done" note.

## Not done yet

- **Backfill not actually executed** — only `--dry-run`. Running it for
  real hits live Ollama embedding calls for ~567 units; left for you to
  trigger when ready rather than run unprompted.
- Citation rendering (frontend: parse `{{source_id:unit_id}}`, link to the
  source viewer) is still open, per §8.
- **Re-run `Research/RAG/eval`'s `stateful` harness** against the
  2026-07-02 `SYSTEM_PROMPT` change (see follow-up section above) to check
  for an answer-accuracy regression.
- **The new documentation-governance files are not committed yet** (see
  status note at top) — 7 root files + 3 local `CLAUDE.md` files, all
  untracked.
- **None of `TEST_STRATEGY.md`'s 8 P0 tests or `RUNTIME_GUARDS.md`'s 7
  runtime assertions have been implemented.** They're blueprints. The
  highest-value next step flagged by `ENFORCEMENT_MAP.md` is that R1
  (`reflection_state` race), R6 (ingestion session-splitting), and R8
  (provenance staleness) are all rated *impossible to detect today*
  because no write-provenance/state-transition logging exists anywhere —
  adding that logging convention once would upgrade all three at once,
  before writing any test.

## Known deliberate simplification (unchanged from Phase 2b)

Ask/Update call Ollama non-streaming — the frontend's progress skeleton
jumps to done instead of animating. Wire shape is unchanged.

## Deferred (recorded in Document A §10 and the plan file, not repeated here)

Provenance-scoped quoting / per-unit source selection UI, Focus mode-picker
UI, lighter opening-turn prompts, out-of-order stage navigation.
