# Reflection flow — concrete implementation walkthrough

> Verified against running code 2026-07-02. This is the only current,
> concrete (UI → handler → route → algorithm → files) account of this
> flow — `docs/HANDOVER.md` §13 and the machine-local plan file
> (`lexical-spinning-kahn.md`) both still describe the deleted
> `gibbs_facilitator_prompt.py` implementation in places. For *why* the
> system is shaped this way, see `REFLECT_Design_Document.md` (intent)
> and `REFLECT_Implementation_Contract.md` (type shapes/mechanism
> contract) — this document only covers *what actually runs*.
>
> **Maintenance note**: this doc will rot the same way HANDOVER.md did
> (see `docs/ISSUES.md` #16) unless it's updated in the same change that
> touches the flow it describes. Function/file names are used as anchors
> in preference to line numbers where possible, since line numbers are
> the first thing to drift.

## 1. Setup — starting a reflection

**UI**: `Frontend/components/home/reflection-setup.tsx` — a 3-stage
wizard (`SetupStage`: `"sources" → "topic" → "ready"`), shown as pills
("01 · Sources", "02 · Topic", "03 · Ready").

**Trigger**: `ReflectionBanner`'s start button → `useChatManagement.ts`'s
`startReflection()`. Notable: this function resets source selection
(deselect-all) **synchronously, before** the `await ensureActiveChat()`
call — a deliberate fix for a tick/untick race (`docs/ISSUES.md` #18),
not an accident of ordering.

- **Sources stage**: user ticks which sources are in scope
  (`source-list-panel.tsx` checkboxes). Sources start deselected — opt-in,
  not opt-out.
- **Topic stage**: either free-text goal, or `groupReflectionTopics()` →
  `POST /reflection/topics` → `reflectionService.group_topics` — an LLM
  call that buckets the included sources' text into 2-5 named topics with
  supporting excerpts, so the user can pick a theme instead of naming one.
- **Ready stage**: `beginReflection()` persists the goal/scope onto the
  `Chat` row (`api.setReflectionGoal` / `api.setReflectionScope` →
  `chatService.update_reflection_goal` / `update_reflection_scope`), then
  calls `generateGibbsQuestion(1, "deep_dive")` — the first real turn.

## 2. The four input-area levers (during an active reflection)

All four render in `Frontend/components/home/chat-input.tsx` when
`reflectionActive` is true. All four ultimately reach either
`/generate-question` (the reflection loop) or `/query-stream` (the
general RAG path) — never both, and never a shared code path.

| Button (label in UI) | Handler (`useChatManagement.ts`) | Wire call | Backend `Mode` | What it does |
|---|---|---|---|---|
| **Answer** | `onReflect` → `submitText("reflect")` | `POST /chats/{id}/messages` (save), then a **silent, fire-and-forget** `streamGeneratedQuestion` with `mode: "reflect"` | `reflect` | Persists the message as the turn's answer. No facilitator reply is shown — the loop runs **Update only**, so Gist/Open Thread absorb what was said without asking another question. |
| **Ask another question** | `onClarify` → `askClarifying()` | `streamGeneratedQuestion` with `mode: "clarifying"`, same `gibbsStep` | `clarifying` | Re-asks at the *same* stage. Full Ask + Update; Open Thread is **not** signaled as resolved. |
| **Answer & next / Answer & finish** | `onContinue` → `continueStage()` | If the box has text: `submitText("reflect")` first, then `advanceGibbsStep()` → `streamGeneratedQuestion` with `mode: "deep_dive"` at `gibbsStep + 1` | `deep_dive` (with `resolve_hint=True`) | The explicit **student-confirmed resolution** of the current Open Thread — this button *is* the confirmation gesture the design calls for, not a separate mechanism. |
| **Ask sources** | `onAsk` → `submitText("ask")` | `POST /query-stream` | *(none — separate persona)* | Deliberate side-channel into the general RAG chat (`generation_registry.py`'s `SYSTEM_PROMPT`), not the facilitator. See `HANDOVER.md`'s "three input-area levers" section for why this is intentional. Feeds back into `reflection_state` only via a best-effort Update hook *after* the RAG reply is already shown. |

Plain form-submit (Enter / send icon) outside an active reflection
defaults to `"ask"` (`handleSubmitText`).

## 3. Backend: the turn loop

Entry point: `POST /generate-question` → `routes/query.py:generate_question`.

```
1. Load/create reflection_state  →  reflectionStateService.ensure_state()
2. mode == "reflect"?
     yes → reflectionLoop.run_reflect_only()   (Update only, no reply)
     no  → reflectionLoop.run_turn()           (full Ask + Update)
3. Save the resulting state       →  reflectionStateService.save_state()
   (isolated in its own try/except — a save failure never discards
   a reply that already generated successfully)
4. Stream the reply (if any) as SSE, after an output safety check
```

`reflectionLoop.py` (`app/services/reflectionLoop.py`) implements the
actual retrieve → Ask → thin-turn-gate → Update sequence:

1. **Retrieve** (`retrieve()`) — real per-unit similarity search
   (`retrieval.retrieve_units`, hard-scoped to the session's included
   `source_ids`, capped to ~250 tokens combined). Zero results is not an
   error — Ask proceeds on Focus/Gist/Open Thread alone.
2. **Ask** (`run_ask()`) — builds messages via
   `prompts/reflection_ask_prompt.py:build_ask_messages`, guarded:
   - **Input guard** (`reflection_guard.injection_intent`): a
     high-precision regex check for prompt-extraction/injection phrasing
     ("ignore previous instructions", "reveal your system prompt", etc.).
     A hit short-circuits to a fixed, in-character redirect — no model
     call at all.
   - **Output guard** (`reflection_guard.output_violations`): after
     generation, checks for an empty/thin reply, leaked scaffolding
     (words like "Gibbs," "stage 3," "as an AI"), markdown formatting, or
     more than one question. One violation triggers **one repair
     regeneration** with the violations named explicitly; a second
     failure falls back to a fixed, scaffolding-free reply
     (`reflection_guard.safe_fallback`).
3. **Thin-turn gate** (`thin_turn.is_thin_turn`) — messages that are
   empty, a known low-information phrase ("ok", "idk", "fine", …), or
   ≤3 words skip the Update step entirely (extraction has nothing to
   work with; the next real turn's follow-up will recapture it).
4. **Update** (`run_update()`) — a separate, JSON-mode Ollama call via
   `prompts/reflection_update_prompt.py:build_update_messages`, producing
   a new `Gist` (one paragraph + citations) and `OpenThread`
   (settled/next/source_ref). **Never raises** — any parse, validation,
   or call failure keeps the prior Gist/Open Thread unchanged and logs to
   `reflection_extraction_failures.log`, so an Update problem can never
   invalidate an Ask reply that already succeeded.

`resolve_hint` (set only when `mode == "deep_dive"`, i.e. the
Continue/Answer&Next lever) is passed into Update as a hint that the
student explicitly confirmed this exchange — not a code-level override;
whether the Open Thread is actually marked settled is still the model's
judgment call.

## 4. State: `reflection_state`

One row per `chat_id` (`ReflectionState` table, `database/models.py`),
holding `sources` (the session's included units), `focus` (goal text,
captured once at first turn), `gist`, and `open_thread` — see
`REFLECT_Implementation_Contract.md` §2 for the type shapes. Loaded via
`reflectionStateService.load_state`/`ensure_state`, written via
`save_state` → `reflectionStateRepository.upsert` (whole-row overwrite,
no history, no per-chat lock — see `INVARIANTS.md` R1 before assuming
concurrent turns on the same chat are safe).

Frontend Gibbs display state (`gibbsActive`, `gibbsStep`,
`gibbsComplete`, …) is separate, ephemeral React state in
`useChatManagement.ts`, reconstructed on load from message history's
`gibbs_step` field — not read from `reflection_state` directly. The two
are related but not the same object (`Frontend/hooks/CLAUDE.md`).

## 5. Stage display (cosmetic layer, no backend role)

`Frontend/lib/gibbs.ts` defines `GIBBS_STEPS`/`GIBBS_STEP_COUNT` (6
stages: description, feelings, evaluation, analysis, conclusion, action
plan) and `GibbsPanel` (`components/home/gibbs-panel.tsx`) renders them
as a segmented ring. **These labels are display-only** — nothing in the
backend enforces stage order, gates advancement, or reads a stage number
to decide what to do (see `CLAUDE.md`'s hard invariants: "no code path
may enforce stage order"). `handleSelectGibbsStep` lets a user jump to
any step directly, regenerating the question for that step — this only
works because the backend never gates on step sequence.

## 6. File map

| Concern | File |
|---|---|
| Setup wizard UI | `Frontend/components/home/reflection-setup.tsx` |
| Input levers UI | `Frontend/components/home/chat-input.tsx` |
| Stage ring UI | `Frontend/components/home/gibbs-panel.tsx`, `Frontend/lib/gibbs.ts` |
| Frontend state/handlers | `Frontend/hooks/useChatManagement.ts` |
| Route | `Backend/app/routes/query.py` (`generate_question`) |
| Turn loop | `Backend/app/services/reflectionLoop.py` |
| State bridge | `Backend/app/services/reflectionStateService.py`, `Backend/app/repositories/reflectionStateRepository.py` |
| Guard | `Backend/app/services/reflection_guard.py` |
| Thin-turn gate | `Backend/app/services/thin_turn.py` |
| Ask/Update prompts | `Backend/app/prompts/reflection_ask_prompt.py`, `reflection_update_prompt.py` |
| Retrieval | `Backend/app/services/retrieval.py` (`retrieve_units`), `Backend/app/services/units.py` (`compute_units`) |
| Topic grouping | `Backend/app/services/reflectionService.py` (`group_topics`) |
| Schema | `Backend/database/models.py` (`ReflectionState`, `Chat.reflection_goal`/`reflection_scope`) |
