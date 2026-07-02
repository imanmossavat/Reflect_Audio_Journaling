# Reflection flow rebuild — status and mental model

**Temporary navigation doc, not a permanent one.** Written to help manage an
in-flight, complex change to the reflection flow and rebuild a mental model
after a lot of fast, multi-phase changes. Delete this file once the change
is done landing and you no longer need to navigate it turn-by-turn — don't
let it fossilize into stale "current state" claims the way `docs/HANDOVER.md`
§13 already did once (see the note left there, pointing back here).

---

## 1. What actually changed, in plain terms

### Before (the code as of commit `632563e`, last night before you started)

A reflection turn had **no persistent memory of the conversation at all**.
Every time the backend needed to ask a question, it rebuilt everything from
scratch out of what the frontend happened to send that request:

- The **entire raw text** of whichever sources were in scope (or, failing
  that, just the single most-recent source) — dumped wholesale into the
  prompt, uncapped, un-searched. No retrieval, no relevance ranking, nothing
  addressable — just a block of text.
- The **last 8 `{question, answer}` pairs**, replayed in full every single
  turn, as the only form of "memory."
- A hardcoded 6-stage dictionary (`STAGES` in `gibbs_facilitator_prompt.py`)
  the model was told about directly — one of three fixed actions (`open` a
  stage / `clarify` within it / `reply` to an answer) was chosen in Python
  and handed to the model as an instruction.
- The **"Answer" button did nothing on the backend at all.** It saved your
  message and stayed silent — client-side only. No extraction, no state
  update, nothing. The only place that turn "lived on" was in the raw
  history array replayed next time.
- No citations. No guard against prompt-injection/extraction attempts. No
  guard against the model leaking its own scaffolding ("as an AI...",
  "stage 3...") into a reply — the only safety layer was Llama Guard's
  general-purpose output check, unrelated to reflection-specific behavior.

In short: **a stateless, replay-everything facilitator**, grounded in raw
text, not in anything addressable or citable.

### After (current code, as of `028701b`)

A reflection turn now has **one small, deliberately-bounded piece of
persistent state per chat** (`ReflectionState`: `Focus`, `Gist`, `Open
Thread`, `sources`), rebuilt incrementally rather than replayed wholesale:

- **Retrieve**: real vector search over the specific *sources* (not the
  whole raw text) — top-5 addressable units, capped ~250 tokens, filtered
  hard to the sources in scope.
- **Ask**: generates the facilitator's reply, grounded in those retrieved
  units + the current `Gist` (one paragraph, "where things stand") +
  `Open Thread` (the one thing being explored right now) — not history
  replay. Wrapped in a reflection-specific **input guard** (blocks
  prompt-injection phrasing before any model call) and **output guard**
  (catches leaked scaffolding/markdown/multi-question replies, with one
  repair-regen before a fixed fallback).
- **Thin-turn gate**: a one-word or filler answer ("ok", "idk") skips the
  next step entirely — cheap, no wasted call.
- **Update**: a *separate* JSON-only call regenerates `Gist`/`Open Thread`
  from the source units + what was just said — never touching the model's
  own prior synthesis uncritically, and **never allowed to fail the turn**:
  a parse/validation error just keeps the old state and logs it, the reply
  the student already saw is never revoked.
- The **"Answer" button now actually does something server-side**: it
  silently fires the Update step only (no visible reply — "one answer per
  question" is preserved), so what you say is genuinely absorbed into Gist/
  Open Thread even though nothing appears on screen. This capability did
  not exist before at all.
- Every claim the facilitator makes can carry an inline citation token
  (`{{source_id:unit_id}}`) back to the exact source unit it came from.
- The entire fixed-stage dictionary (`gibbs_facilitator_prompt.py`,
  `STAGES`, `open`/`clarify`/`reply` actions) is **deleted**. The model is
  never told a stage name exists. Stages are now purely a frontend display
  ring (`Frontend/lib/gibbs.ts`) with zero backend role.

### Why this change, specifically

This maps directly onto failure modes Design Doc A names explicitly
(§5, §7):

- **"Interrogation" feeling** — caused by grounding questions in a ledger of
  what the student already said, and re-checking it off. Fixed by grounding
  in the *source material* instead (retrieved units), with Gist as a light,
  regenerated summary rather than an accumulating checklist.
- **Stage-as-gatekeeper** — the old code hardcoded stage names and actions
  directly into what the model was told to do. That's exactly the "phase
  acting as code-level gatekeeping" Doc A says must not survive. Deleting
  `gibbs_facilitator_prompt.py` is the literal mechanism of that fix, not
  just cleanup.
- **Gist drift** — a rolling summary that edits itself indefinitely
  compounds distortion. Fixed by regenerating Gist mostly from source units
  + the current exchange each time, dropping any carried-over sentence that
  no longer has a traceable citation (confirmed present, verbatim, in
  `reflection_update_prompt.py`'s instruction text).
- **No memory of "Answer" turns** — previously a real gap: agreeing/adding
  detail via the Answer button was invisible to the system. Now it updates
  state even while staying silent in the UI.

---

## 2. Where Doc A / Doc B / REFLECTION_FLOW.md match reality, and where they don't

**Context you gave me**: Doc A and Doc B were written by you, after the
fact, describing what an intern built without exactly following your
(evolving) wishes. So they're not guaranteed spec-first truth — they're
your account of intent, possibly ahead of, behind, or diverging from what's
actually running. Below is what I could actually verify against the code.

### Confirmed accurate

- **`docs/REFLECTION_FLOW.md`** — matches the running code exactly
  everywhere I checked (turn loop, four levers, guard behavior, thin-turn
  gate, file map). Trust this one first.
- **Doc B §6's Gist drift-mitigation rule** — verbatim in
  `reflection_update_prompt.py`'s instruction text. Real, not aspirational.
- **Doc B §9's "hard deletions"** (transcript replay, stage gating, fact
  ledger) — all genuinely gone from the diff. `gibbs_facilitator_prompt.py`
  deleted; no history-window replay in the new prompts; no fact ledger
  anywhere in `reflectionLoop.py`.
- **Doc A's "existing Gibbs flow" description (§1)** — accurate: the old
  code already had three per-turn moves (answer+next, answer+another
  question, consult sources), the rebuild changed the mechanism underneath,
  not the lever concept. The four-lever *shape* (Answer / Ask another
  question / Answer & next / Ask sources) mostly pre-dates this rebuild;
  what's new is what runs underneath each one.

### Real gaps — reality diverges from what the docs say

1. **`Focus` is not the enum Doc B specifies — and the empty-default is
   reachable through a first-class UI path, not an edge case.** Doc B §2
   types `Focus.value` as `"explore_why" | "decide_next" | "talk_it_through"
   | string`, and §3 says explicitly: *"There is no guessed or defaulted
   Focus — the picker is part of session start, not optional."* The actual
   code (`reflectionStateService.ensure_state`) reuses the pre-existing
   free-text `reflection_goal` as-is, with **no picker UI**, and **defaults
   it to `"reflect on this entry"` when empty**:
   ```python
   # Backend/app/services/reflectionStateService.py, ensure_state()
   focus_value = (chat.reflection_goal or "").strip() or "reflect on this entry"
   ```
   Verified this is reachable via normal use, not just legacy chats/direct
   API calls: `reflection-setup.tsx` has an explicit **"Skip setup"** button
   on the *Sources* stage itself (line ~88) that jumps straight to "Ready"
   with the goal forced empty:
   ```tsx
   onClick={() => { onChangeGoal(""); onClearScope(); setStage("ready") }}
   ```
   The function's own docstring admits this was "simplified per direct
   instruction," but Doc B was never updated to reflect it. Worth deciding:
   update Doc B to match, or treat the picker as still-owed.

2. **`reflection_state.sources` doesn't hold real per-unit data.** Doc B §2
   types it as `SourceUnit[]` — implying specific retrieved/selected units.
   In practice, `ensure_state` stores one placeholder per whole *source*
   (`unit_id="full"`, full source text), not real paragraph/segment units.
   Actual per-unit retrieval happens fresh every turn via `retrieve_units`
   and is never read from this stored list. Functionally harmless (nothing
   depends on the placeholder being real units) but the field means
   something narrower than Doc B implies.

3. **`Source.verified` is schema-only — confirmed zero consumers.** Doc A
   §6.2 says unverified material must be excluded from reflection/RAG by
   default. `retrieval.py`'s `retrieve_units()` filters only on
   `kind == "unit"` and `source_id IN (...)`:
   ```python
   filters = MetadataFilters(filters=[
       MetadataFilter(key="kind", value="unit", operator=FilterOperator.EQ),
       MetadataFilter(key="source_id", value=[str(s) for s in source_ids], operator=FilterOperator.IN),
   ])
   ```
   No `verified` filter, and a grep of `Backend/app/services/` and
   `Backend/app/routes/` for any read of `.verified` returns nothing. Doc B
   §2.1 already flags this honestly as future "consumer-side work," so
   this isn't a doc/reality mismatch so much as a confirmed-still-open
   item — listed here so it doesn't get assumed done.

4. **Citation rendering is backend-only, frontend side unverified.** Ask
   emits `{{source_id:unit_id}}` tokens; whether the chat UI currently
   parses and links them, or just prints the raw token as literal text, was
   not checked in this pass (`SESSION_HANDOFF.md` lists it as open — worth
   a quick manual check before assuming either way).

5. **`docs/HANDOVER.md` §13** — still describes the deleted
   `gibbs_facilitator_prompt.py` (stage dict, `open`/`clarify`/`reply`
   actions, 8-turn history replay, 2000-char raw dump) as current. Flagged
   in place; not corrected.

6. **Focus-shift suggestions are computed and then silently discarded.**
   Doc A §6 says the AI "may suggest a change" to Focus (never apply one
   itself). The Update call genuinely produces this —
   `reflectionLoop.TurnResult.focus_shift_suggested` is populated every
   turn — but `grep -n "focus_shift" Backend/app/routes/query.py` returns
   zero hits, and so does `grep -rn "focus_shift|focusShift" Frontend/`.
   The route never forwards it on the SSE payload and nothing on the
   frontend reads it. Half-built: computed, never surfaced.

7. **The "words in the student's mouth" constraint (Doc A §7, a hard
   constraint "not stage-specific") is prompt-only, not guard-enforced.**
   `reflection_guard.py`'s `output_violations()` runs exactly four checks —
   `is_thin`, `novel_leak` (scaffolding/self-disclosure regex),
   `format_violations` (markdown/quote-wrapping), `question_count` — none
   of which detect an asserted feeling/motive/interpretation, hedged or
   not. The constraint exists only as an instruction in
   `reflection_ask_prompt.py`'s `RESPONSE_RULES`: *"Never label an emotion,
   motive, or interpretation the student did not state."* If the model
   ignores it, nothing catches it downstream.

8. **Quote-anchored and multiple-choice question forms (Doc A §5, "two
   lighter-weight forms are preferred where they fit") don't exist in the
   code at all.** Full read of `reflection_ask_prompt.py` — every
   instruction path produces a fully open question. No mechanism for
   pairing a question with a verbatim quote or offering reactable options
   anywhere in the prompt or the loop.

### Confirmed *not* touched by this rebuild (consistent with Doc A §10)

Advisor view, closing-artifact generation, hierarchical tags, per-document
inclusion rules, provenance-scoped quoting, out-of-order stage navigation —
Doc A lists these as explicitly deferred, and nothing in the commit range
below touches any of them. No surprise, just confirming nothing slipped in
by accident.

---

## 3. Commit range and file map (reference)

Last night's rebuild = **9 commits, `310e981` → `028701b`**
(2026-07-01 22:08 → 2026-07-02 00:07).

- **`632563e`** (21:30) — the marker right before. Docs-only. Not part of
  the rebuild; used as the "before" snapshot above.
- **`f27a68a`** / **`db9f79f`** (this morning) — a separate documentation-
  governance pass (`CLAUDE.md`, `INVARIANTS.md`, etc.) and the
  `REFLECTION_FLOW.md` writeup. Describes/binds the rebuild, isn't new
  reflection-flow code.

| Commit | Time | What it did |
|---|---|---|
| `310e981` | 22:08 | Doc A edits only |
| `8cd5f3c` | 22:37 | `Source.provenance`/`verified` columns + migration |
| `b718aed` | 22:43 | New `reflection_ask_prompt.py`, `reflection_update_prompt.py`, first `reflectionLoop.py` |
| `1f1a223` | 22:58 | `reflection_guard.py`, `reflectionStateService.py`, `reflectionStateRepository.py`, `ReflectionState` table + migration, `query.py` route rewrite, frontend lever wiring |
| `20e58e7` | 23:01 | docs only |
| `41916d3` | 23:22 | Real per-unit retrieval (`units.py`, `retrieval.py`); **deletes `gibbs_facilitator_prompt.py`**; backfill script |
| `b2fd6b3` | 23:47 | Live-test bugfixes: `query.py`, `generation_registry.py`, `reflectionLoop.py`, `safety.py` (removed S6 from the support-card trigger — false-positived on ordinary planning talk, `docs/ISSUES.md` #19) |
| `b87a39e` | 00:06 | `HANDOVER.md` only |
| `028701b` | 00:07 | `prompt.py` — `SYSTEM_PROMPT` small-talk-branch fix (RAG side-channel bug) |

**New files:** `reflectionLoop.py` (315 lines), `reflection_guard.py` (174),
`reflectionStateService.py` (66), `reflectionStateRepository.py` (40),
`reflection_ask_prompt.py` (93), `reflection_update_prompt.py` (101),
`units.py` (28), `scripts/backfill_source_units.py`, `scripts/run_reflection_turn.py`.

**Deleted:** `Backend/app/prompts/gibbs_facilitator_prompt.py` (166 lines).

**Modified (non-trivial):** `routes/query.py` (128 lines — the route
rewrite), `database/models.py` (+34 — `ReflectionState`, `Source.units`/
`provenance`/`verified`), `services/retrieval.py` (+64 — `index_units`/
`retrieve_units`), `services/generation_registry.py` (+63 — post-RAG
best-effort Update hook), `schemas/journalSchemas.py` (`Mode` enum:
`reflect` added, `reply` removed as dead), `services/sourceService.py`
(+16 — units hook into ingest), `services/prompt.py` (+14/-2),
`services/safety.py` (+12 — S6 removal), `Frontend/hooks/useChatManagement.ts`
(+46), `Frontend/lib/api.ts` (+4), 3 new Alembic migrations.

**Tests (new/changed):** `test_reflection_loop.py`, `test_reflection_guard.py`,
`test_reflection_state.py`, `test_units.py`, `test_unit_retrieval.py`,
`test_reflection_prompt_assembly.py`, `test_generation_registry.py`,
`test_safety.py`.

**Docs touched in the same range:** `docs/SESSION_HANDOFF.md`,
`docs/ISSUES.md`, `docs/HANDOVER.md`, `docs/REFLECT_Design_Document.md`,
`docs/REFLECT_Implementation_Contract.md`.

---

## 4. Not done yet (per `docs/SESSION_HANDOFF.md`, as of 2026-07-02)

- Real backfill (`scripts/backfill_source_units.py`) only `--dry-run`'d,
  never actually executed against live data.
- Citation rendering on the frontend — open, per §2 item 4 above.
- `Research/RAG/eval`'s `stateful` harness not re-run against the
  `028701b` `SYSTEM_PROMPT` change — possible answer-accuracy regression
  risk, unchecked.
- None of `TEST_STRATEGY.md`'s 8 P0 tests or `RUNTIME_GUARDS.md`'s 7
  runtime assertions implemented — blueprints only.
- `docs/ISSUES.md` #21 — related, unconfirmed watch item, not fixed.
- Doc B's `Focus` picker (§2 gap above) — either build it, or update Doc B
  to match the simplified version actually shipped.
- `Source.verified` exclusion behavior (§2 gap above) — flag exists, no
  consumer reads it yet.
