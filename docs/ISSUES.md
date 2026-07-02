# REFLECT — Codebase Issues Found During Review

> Originally produced 2026-06-30, updated 2026-07-01 (torch extras fix,
> device-availability validation, Chroma orphaned-vector fix, transcript
> provenance, repository-level DB tests, tag-system audit — see
> `docs/TAGS.md`, `docs/DB_TESTING_PROPOSAL.md`) and again later the same
> day (#18-#21, found live-testing the rebuilt reflection flow — see
> `docs/SESSION_HANDOFF.md`). Every item below was re-checked against the
> code as it stands now, not carried over blindly. Issue numbers are
> load-bearing: `#1`, `#9`, `#12`, `#15`, and `#17` are referenced directly
> in code comments and test `xfail` reasons (`Backend/pyproject.toml`,
> `Backend/tests/repositories/*`, `Backend/tests/test_pyproject_torch_sources.py`)
> — don't renumber without updating those references too.

---

## Fixed since 2026-06-30

### 1. `--extra cuda` / `--extra cpu` — now routed to real, distinct indexes

**Files**: `start.sh`, `start.ps1`, `Backend/pyproject.toml`

`pyproject.toml` now defines `cpu` and `cuda` as real optional-dependency
extras (plus `ml`, kept as the CPU alias Mac/Linux already used), each
routed to a distinct PyTorch wheel index via `[tool.uv.sources]`, and
declared mutually exclusive via `[tool.uv].conflicts` so a single resolve
can't silently satisfy one extra with the other's wheel. `start.sh` and
`start.ps1` both pick `cpu`/`cuda` consistently (no more `ml`/`cpu` mismatch
between the two scripts).

`Backend/tests/test_pyproject_torch_sources.py` guards the regression this
used to cause (both extras pinning `torch==2.8.*` with no index routing, so
`uv sync --extra cuda` silently installed the CPU wheel) — it asserts the
two extras map to different index names and that the `cuda` index URL
contains a CUDA tag (e.g. `cu128`).

### 2. `test_journalService.py` — rewritten, no longer stale

**File**: `Backend/tests/services/test_journalService.py`

Previously mocked a removed API (`update_source_text`, old synchronous
`process_source`, `index_chunks(journal_id=...)`). Rewritten against the
current `sourceService` API. Full suite is now **121 passed, 2 xfailed**
(`uv run --extra dev --extra ml pytest -q` from `Backend/`) — the 2 xfails
are the intentional, documented ones in issue #12 below, not failures.

### 3. `ColoredFormatter` dead code — removed

**File**: `Backend/app/logging_config.py`

The file has been rewritten entirely: `LOG_LEVEL` env var controls console
verbosity, file logging always captures `DEBUG`, and a long list of noisy
third-party loggers (`httpx`, `torch`, `chromadb`, `multipart`, `fsevents`,
`matplotlib`, `torio`, `fsspec`, `urllib3`, `lightning`, `numba`, …) is
capped at `WARNING`. No dangling, unregistered handler remains.

### 9. CUDA PyTorch index URL — configured

**File**: `Backend/pyproject.toml`

Same fix as #1: `[tool.uv.sources]` now points the `cuda` extra at a
CUDA-tagged PyTorch index (distinct from the `cpu`/`ml` extras' index), so
`torch==2.8.*` actually resolves to a CUDA wheel when `--extra cuda` is
used.

### Bonus (not in the original list): orphaned Chroma vectors on reprocess

**File**: `Backend/app/services/sourceService.py` (`_process_source_sync`)

Reprocessing an edited source deleted its SQL `Chunk` rows but never
deleted the matching ChromaDB vectors, leaving stale, still-searchable
embeddings behind (the same class of bug already avoided in
`chatService.reindex_chat`). Fixed today by deleting the matching Chroma
vectors (`where={"source_id": ...}`) whenever SQL chunks are deleted before
a re-chunk/re-index. No dedicated regression test file, but covered
indirectly by `tests/services/test_journalService.py`'s reprocess cases
(confirmed by reverting the fix locally and observing the tests fail).

---

## Still open

### 4. `ChatMessage.role` naming is inverted

**Files**: `Backend/database/models.py`, `Backend/app/services/generation.py`

`role = "question"` means the **AI/facilitator** spoke; `role = "answer"`
means the **human** spoke — the opposite of what a new developer would
expect. Silently corrected in `generation.py`'s `to_chat_messages()`
(`"answer"` → `role: "user"`, `"question"` → `role: "assistant"`). Anyone
touching `ChatMessage.role` directly without knowing this will get it
backwards.

**Fix**: a migration renaming to `"user"`/`"assistant"`, or at minimum a
prominent comment on the field in `models.py`.

### 5. `start.ps1` uses lowercase `frontend` path — directory is `Frontend`

**File**: `start.ps1` (both `Set-Location "$root\frontend"` occurrences)

Still present. Works today only because Windows paths are case-insensitive;
inconsistent with the rest of the script and would break on a case-sensitive
filesystem.

**Fix**: change both occurrences to `"$root\Frontend"`.

### 6. `ragas` and `rapidfuzz` are unused production dependencies

**File**: `Backend/pyproject.toml`

`strip-markdown` has since become a real dependency — `sourceService.py`
now calls `strip_markdown.strip_markdown(text)` for markdown sources before
chunking, so it's no longer dead. `ragas==0.4.3` and `rapidfuzz==3.14.5`
remain in the main `dependencies` block but are still not imported anywhere
in `Backend/app/`; `ragas` is only relevant to `Research/`.

**Fix**: move `ragas` and `rapidfuzz` to a `dev`/`eval` optional extra.

### 7. `rag.py` re-export facade is fragile

**File**: `Backend/app/services/rag.py`

Unchanged. Re-exports symbols from four sub-modules via explicit imports
plus a `__getattr__` fallback. A new attribute added to a sub-module and
accessed via `from app.services.rag import X` either returns `None`
silently or raises a generic `AttributeError` with no hint about the real
module.

**Fix**: explicit `from .retrieval import *`-style re-exports so missing
symbols fail loudly, or migrate callers to import from the real modules and
drop the facade.

### 8. `TranscriptionManager` still caches `model`/`language` at init

**File**: `Backend/app/services/transcription.py`

Partially addressed today, not fully: `__init__` now validates the
configured **device** against real hardware (`device_available()`, see the
device-detection note in #14) and falls back to `cpu` with a logged warning
instead of silently using an impossible device. It still reads
`settings.WHISPER_MODEL` and `settings.LANGUAGE` once at construction time,
so changing the Whisper model or language in Settings has no effect until
the manager is re-instantiated (next process restart, or lazily on the
first transcription after a code path that recreates it — not guaranteed
today).

**Fix**: register an `on_change` listener in `settings_service` to
re-instantiate (or refresh) the manager when these settings change.

### 10. ChromaDB collection name is hardcoded with no versioning

**File**: `Backend/app/services/chroma.py` (`COLLECTION_NAME = "source_chunks"`)

Unchanged. If the embedding model or chunking strategy changes in a way
that invalidates existing vectors, there's no migration path — you have to
delete `Backend/database/chroma/` and reprocess every source.

**Fix**: include the embed model name or a version tag in the collection
name (e.g. `"source_chunks_v2"`) so old and new vectors can coexist during a
transition.

---

## New — found during today's (2026-07-01) tag-system and provenance audit

### 11. Path A tag extraction (`/extract-tags`) is dead from the user's perspective

**Files**: `Backend/app/routes/query.py`, `Backend/app/services/tagService.py`,
`Frontend/lib/api.ts`

There are two independent LLM tag-generation pipelines (full detail in
`docs/TAGS.md` §2):

- **Path A** — `extract_and_store_tags()`, reachable only via
  `POST /extract-tags`. Richer output (`{name, summary, quotes}` with
  verbatim substrings, built for highlighting that nothing currently uses).
  `Frontend/lib/api.ts`'s `extractTags()` client function exists but is
  called from **zero** components (confirmed by grepping the whole
  `Frontend/` tree). `sourceService._process_source_sync` never imports
  `tagService`, so it's not part of automatic ingest either — the
  `HANDOVER.md` pipeline diagram's old "→ extract+store tags (LLM)" step
  does not actually happen automatically; only summary generation is
  automatic.
- **Path B** — `suggest_tags_via_llm()` → suggest/confirm flow, the one
  actually wired into the UI (Enrich Source Modal).

Net effect: almost nothing in real usage ends up `origin="llm"` in the
database — that value exists in the schema for a pipeline nothing calls.

**Fix**: wire Path A into the UI (e.g. a "deep extract" action) or remove it
as dead code; either way, stop maintaining two divergent tag-generation
prompts if only one will ever run.

### 12. Manual edits never refresh the `derived_meta` provenance stamp

**Files**: `Backend/app/repositories/sourceRepository.py` (`update_source_fields`),
`Backend/tests/repositories/test_source_provenance.py`

Editing a source's summary or transcript text through the normal
manual-edit path (`update_source_fields`, used by the PATCH endpoint) never
touches `derived_meta`. The stamp keeps asserting the original AI generation
(model, prompt version, timestamp) as if the text were never touched by a
human. Confirmed real and pinned by two `xfail(strict=True)` tests in
`test_source_provenance.py` — `strict=True` means they'll flip to a hard
failure (forcing a test update alongside the fix) the moment someone
addresses this, rather than silently passing.

This is the concrete, already-reproduced instance of the gap that the
in-progress provenance retrofit (Document A §6.1 / Document B, see
`docs/SESSION_HANDOFF.md`) is meant to close — not a new report about that
future work, but a pinned test of today's actual behavior.

**Fix**: not yet decided — depends on the provenance model shape Document B
adopts (clear the stamp, flag it stale, or replace it) — see
`docs/SESSION_HANDOFF.md`'s "active thread" section before starting.

### 13. At least half a dozen `Frontend/lib/api.ts` client functions are unused

**File**: `Frontend/lib/api.ts`

Grepped every exported `api.*` method against the rest of `Frontend/` (app,
components, hooks, context). Confirmed zero call sites outside `api.ts`
itself for: `getUnprocessedSources`, `getSourceChunks`, `saveAnswer`,
`transcribeSource`, `extractTags` (see #11). There may be more not yet
checked — this list is a confirmed floor, not an exhaustive count.

**Fix**: either wire these up (some, like `transcribeSource`, may reflect an
intended-but-unbuilt retry-transcription UI) or delete them along with any
now-unused backend routes/schemas they were the sole client of.

### 14. Device-availability detection is implemented three separate times

**Files**: `start.sh`, `start.ps1`, `Backend/app/services/settings_service.py`,
`Backend/app/routes/settings.py`

Three independent implementations of "is this compute device actually
available on this machine," none sharing code:

1. **Shell** (`start.sh`/`start.ps1`) — `nvidia-smi` presence/exit-code
   check, used only to pick the `--extra cpu`/`cuda` uv sync flag at
   startup.
2. **`settings_service.py`** — `device_available()` / `best_available_device()`,
   using `torch.cuda.is_available()` / `torch.backends.mps.is_available()` /
   a ROCm/HIP check. Used to validate a configured device before
   `TranscriptionManager` uses it (today's fix, see #8).
3. **`routes/settings.py`** (`/settings/devices`) — its own, separately
   written `torch.cuda.is_available()`/mps/ROCm checks to populate the
   device dropdown in Settings.

These can drift (e.g. one gains ROCm detail and another doesn't) since none
call the others.

**Fix**: have `routes/settings.py` call `settings_service`'s device-detection
functions instead of reimplementing them; the shell-level `nvidia-smi` check
is a separate concern (picking a uv extra before Python even runs) and can
stay separate, but should at minimum be commented as intentionally
independent so it isn't "fixed" into a false consolidation.

### 15. A confirmed LLM tag suggestion is indistinguishable from a manual tag

**Files**: `Backend/app/routes/tags.py` (`confirm_suggested_tags`),
`Backend/app/repositories/tagRepository.py`

`confirm_suggested_tags` calls `add_tag_to_source` with no `origin=`
argument, so a user-approved LLM suggestion is persisted with
`origin="user"` — identical to a hand-typed tag. Pinned (not `xfail`, since
there's no confirmed "correct" shape to assert toward yet) by
`test_tag_provenance.py::test_confirmed_llm_suggestion_is_indistinguishable_from_a_manual_tag`.
Practically: this history is already unrecoverable — there's no timestamp
on `SourceTag` and no logging in the tag write path, so a future fix can
only classify tags written after it ships, not backfill today's data
honestly.

**Fix**: part of the same provenance retrofit as #12 — likely a third
`origin` value (e.g. `"llm_confirmed"`) going forward, with no way to
recover history for existing rows.

### 16. `docs/HANDOVER.md`'s testing section and pipeline diagram were stale

**File**: `docs/HANDOVER.md` (fixed as part of today's doc pass — see the
`docs/HANDOVER.md` diff)

Two independent staleness bugs in the handover doc itself, found while
cross-checking it against current code: (a) §5.2's pipeline diagram listed
automatic tag extraction as a real step, which #11 shows is not true; (b)
§10's testing table pre-dated `test_thin_turn.py`, `test_settings_service.py`,
`test_transcription.py`, the whole `Backend/tests/repositories/` directory,
and `test_pyproject_torch_sources.py`, and still described
`test_journalService.py` as stale after it had been rewritten (#2). Both
fixed in this pass. Flagging as its own issue because it's a recurring
failure mode worth watching for, not a one-off: **the handover doc drifts
from the code faster than it gets re-read** — worth a habit of updating it
in the same commit as the pipeline/test changes it describes, not as a
separate later pass.

### 17. Confirmed schema/migration drift on four columns

**Files**: `Backend/database/models.py`, `Backend/migrations/versions/`

`uv run alembic check` fails today, reporting `modify_type` operations on
`chat_message.thinking`, `source.text_html`, `source.summary`, and
`source.summary_html` — hand-written migrations declared these `sa.Text()`,
but the SQLModel classes declare bare `str`, which SQLModel maps to
`AutoString()` (effectively `VARCHAR` with no length). Confirmed
independently by running `alembic check` directly (not just trusting the
test), and by `test_migration_drift.py`, which round-trips long strings
through a real Alembic-migrated schema to prove the drift is harmless on
SQLite today (TEXT and unbounded VARCHAR are storage-identical there) —
but it's exactly the kind of drift a future migration (e.g. the provenance
retrofit's) could turn into a real bug if it changes column types without
matching the model.

**Fix**: not urgent given today's harmless-on-SQLite finding, but should be
reconciled — either regenerate the affected migrations to declare
`AutoString()`/unbounded `VARCHAR` to match the models, or accept the drift
explicitly with a comment in `models.py` so `alembic check` failures don't
get treated as a surprise later.

---

## New — found live-testing the rebuilt reflection flow (2026-07-01)

### 18. `startReflection` deselect-all raced against the sources panel opening — Fixed

**File**: `Frontend/hooks/useChatManagement.ts` (`startReflection`), triggered
from `Frontend/app/page.tsx:397-400`

Clicking "Start reflection" opened the sources sidebar (`sidebar.openRight()`)
synchronously, in the same click handler that fired `chats.startReflection()`
async. That function only ran its "deselect every source" reset *after*
`await ensureActiveChat()` resolved (a real network call, `POST /chats`, when
no chat was active yet). If a user ticked a source checkbox while that
request was still pending, the tick landed, then the delayed reset silently
reverted it — visible as "tick, then immediate untick, then it works a moment
later" once the pending call finished. Reproduced live; heavy background
polling (three independent poll loops, see #21) widened the window enough to
make it easy to hit.

**Fix**: moved the `setRawSources` deselect-all to run synchronously, before
the `await`, closing the race window entirely. `gibbsActive`/`gibbsSetup`
etc. still wait for `ensureActiveChat()` to succeed, unchanged, so a failed
chat-creation still leaves the wizard closed exactly as before.

Searched for the same shape elsewhere (open UI, then an async function later
resets state a user might touch in the meantime) — no other confirmed
instance; see #21 for one unconfirmed, lower-confidence candidate.

### 19. Llama Guard's S6 ("Specialized Advice") false-positived the support card onto ordinary conversation — Fixed

**File**: `Backend/app/services/safety.py` (`CATEGORY_TO_KIND`)

`S6` was mapped to the same "support" wellbeing kind as `S1`/`S2`, alongside
`S11` → `self_harm`. Reproduced live: a RAG answer discussing career
strategy and next steps ("what specific actions... feel most critical")
tripped `S6` on the 1B guard model and surfaced the "It's okay to reach
out... de Luisterlijn" card on completely benign planning conversation.
Looking at the taxonomy, this isn't really a mapping-severity problem (the
`support` card is already a deliberately softer tier than `self_harm`, not
identical to it — see `Frontend/components/home/crisis-support-card.tsx`) —
it's a category-relevance problem: S6 flags content resembling
unqualified professional advice (medical/legal/financial), a
misinformation/liability signal, not a wellbeing one. Nothing about "this
looks like specialized advice" correlates with the user's emotional state,
so it was always going to false-positive on ordinary goal/strategy talk.

**Fix**: removed `"S6": "support"` from `CATEGORY_TO_KIND`. Only `S1`, `S2`,
`S11` remain — the categories that actually plausibly correlate with
distress. Regression tests: `Backend/tests/services/test_safety.py`.

### 20. Reflection-state persistence failures could discard an already-successful reply — Fixed, three call sites

**Files**: `Backend/app/services/reflectionLoop.py` (`run_update`),
`Backend/app/routes/query.py` (`generate_question`),
`Backend/app/services/generation_registry.py` (`_update_reflection_state_after_rag_turn`)

Found by tracing #19's investigation forward, not live-reproduced — a
self-review pattern-match against the same "silent failure that should have
been contained" class as the units-hook bug fixed earlier the same day (see
`docs/SESSION_HANDOFF.md`). Three layers of the same bug, root to
outermost:

1. `reflectionLoop.run_update` guarded JSON/validation failures from the
   Update call but not the `ollama.chat(...)` call itself — a connection
   drop or timeout there propagated uncaught, discarding whatever `run_ask`
   had *already* generated several layers up (`run_turn`/`run_reflect_only`
   call `run_update` with no try/except of their own).
2. `/generate-question`'s route persisted `reflection_state` inside the same
   `try` block as the reply generation — a save failure after a successful
   reply reported the whole turn as errored instead of just logging the lost
   Gist/Open Thread update.
3. `generation_registry`'s post-"Ask sources" Update hook had the same
   shape: a failure there could report an already-saved RAG answer as
   failed.

All three violate the same explicit design rule (Contract §6/§10: Update
failures must never block Ask's reply). Only #1 was literally named in the
contract's failure table (JSON/validation only); the same rule has to extend
to *any* Update failure, or a caller several layers up ends up discarding
real, already-generated work over an Update-only problem.

**Fix**: widened `run_update`'s catch to any exception (still keeps prior
state, still logs, still never raises); wrapped the route's `save_state`
call and the registry's whole Update hook each in their own isolated
try/except that logs and continues rather than failing the turn. Regression
tests: `test_reflection_loop.py::test_run_update_keeps_prior_state_on_unexpected_model_call_failure`,
`test_generation_registry.py` (new file, 3 tests). The route-level fix has
no dedicated test — this repo has no route-level (TestClient) test
precedent yet, same gap noted for the route itself in the original plan.

### 21. Three independent frontend poll loops hit the backend simultaneously; one merge path is an unconfirmed watch item

**Files**: `Frontend/hooks/useChatManagement.ts` (`GET /chats`, 5000ms,
always running), `Frontend/hooks/useSourceManagement.ts` (`GET
/sources?since_id=N`, 5000ms, always running; a second `processingSources`
poll, 2500ms, only while any source is non-terminal)

Not a confirmed bug on its own — flagging because it's what widened #18's
race window enough to make it easy to hit live, and because Phase 3's new
units-computation step (`sourceService.py`, see `docs/SESSION_HANDOFF.md`)
adds real wall-clock time to the `"chunking"` status, keeping sources
non-terminal (and the 2500ms poll running) slightly longer than before.
Investigated the `processingSources` poll's merge logic for the same
clobber shape as #18: it does **not** clobber `included` (confirmed — only
`status`/`content` fields are touched), but it does unconditionally
overwrite a source's `content` from the server whenever the poll response
carries text. No live UI path that edits `content` while a source is still
processing was found, so this is a plausible-shape, unconfirmed risk, not a
reproduced bug — recorded so it isn't lost, not treated as fixed or urgent.

**Fix**: none applied — no reproducible bug to fix. Worth a second look if
an in-flight-source content editor is ever added.

### 22. The same poll loops from #21 drowned the console in access-log noise — Fixed (logging filter + visibility-gated polling)

**Files**: `Backend/app/logging_config.py`, `Frontend/hooks/useChatManagement.ts`,
`Frontend/hooks/useSourceManagement.ts`

Separate from #21's data-race question: the three poll loops it describes are
each independently running in **every open tab**, and every request they make
produced a standard uvicorn access-log line (`INFO: 127.0.0.1:xxxxx - "GET
/chats HTTP/1.1" 200 OK`) at INFO level to both console and `logs/app.log`.
With two or three tabs open — an ordinary dev session, not an edge case — that
was a `GET /chats` or `GET /sources`/`GET /source/{id}` line every 1-2 seconds
on average, interleaved with the actual debug output being watched. Pure
noise: none of these lines carry information a developer doesn't already know
("the poll fired again"), and they make it materially harder to spot the
signal (an error, a slow request, a one-off log line) live during debugging.

Not a data-correctness issue and not the same as #21 — #21 is about a
possible state-clobber bug in the poll's merge logic; this is purely about
log signal-to-noise. Flagged separately per the review comment that surfaced
it.

**Fix, part 1 (logging)**: `logging_config.py` now attaches a `logging.Filter`
to the `uvicorn.access` logger that drops **successful (2xx) GET** requests to
`/chats`, `/sources` (with or without `?since_id=`), and `/source/{id}` —
exactly the three polled routes — while leaving every other route, every
non-GET method, and every non-2xx status (including a failing poll — that's
real signal) logged exactly as before. See the filter's docstring for why
it's safe regardless of whether it's installed before or after uvicorn's own
`configure_logging()` call reconfigures that logger's handlers.

**Fix, part 2 (actual request volume)**: all three `setInterval` poll loops
(`useChatManagement.ts`'s `/chats` poll, `useSourceManagement.ts`'s `/sources`
poll and its `processingSources` poll) now skip their tick when
`document.visibilityState === "hidden"`, and each fires one immediate resync
on `visibilitychange` back to `"visible"` so a tab you switch back to isn't
stale for up to 5s. A backgrounded tab — the common case when someone has
several REFLECT tabs open but is only looking at one — now makes zero polling
requests instead of one every 2.5-5s. The intervals themselves, their
cadence, and the "no shared coordination between the two hooks" invariant
(`Frontend/hooks/CLAUDE.md`) are all unchanged; each effect independently
decides whether to skip its own tick, so nothing here couples the two hooks
together.

**Not done**: two or more tabs simultaneously *visible* (e.g. side-by-side
windows) still each poll independently — this fix only collapses *background*
tabs to zero, it doesn't add cross-tab leader election. If that residual
volume ever matters, a `BroadcastChannel` leader-election (only one visible
tab polls, broadcasts results to the others) or a longer interval with
backoff would be the next step; neither has been attempted.

---

## New — found handling a live port-8000 conflict (2026-07-02)

### 23. `start.sh` port-8000 auto-recovery — needs live verification

**File**: `start.sh` (`free_stale_port`, called as
`free_stale_port 8000 "$ROOT/Backend/.venv"` before "Start backend in
background")

A real run hit the failure this was written to fix: a stale backend from a
previous `./start.sh` still held port 8000, uvicorn died with "Address
already in use," and the script pressed on anyway — printing "Both servers
are starting" while the backend was actually dead. The user had to manually
`lsof -i :8000` + `kill -9` to recover.

Added `free_stale_port`: kills whatever's on port 8000 only if its command
line contains this exact checkout's venv path (`$ROOT/Backend/.venv` —
tightened from an earlier, too-generic `"app.main:app"` match that could
have false-positived on any other FastAPI project using the same idiomatic
`app/main.py` layout). If the port is held by something that doesn't match,
the script now fails fast with the PID/command and a copy-pasteable
`kill -9 <PID>` instead of limping forward with a dead backend.

Verified so far only against disposable Python socket-listener fixtures on
scratch ports (both the "ours → auto-kill" and "not ours → leave alone +
error" branches passed). **Not yet verified** against a real leftover
`start_backend.py`/uvicorn process in a full end-to-end `./start.sh` run —
in particular, uvicorn's `--reload` mode forks a `multiprocessing.spawn`
worker that also binds LISTEN on the port (confirmed via `lsof` during the
investigation), and the fix's kill-all-pids-in-the-group logic hasn't been
exercised against that actual topology, nor against the script's `set -e` /
trap / background-job interactions end-to-end.

**Fix**: not a code fix — a verification task. Reproduce a genuine leftover
backend on 8000 (e.g. run `./start.sh`, Ctrl+D the terminal instead of
Ctrl+C, then run `./start.sh` again) and confirm auto-recovery works
cleanly.

---

## Summary table

| # | Severity | Status | Issue | File(s) |
|---|---|---|---|---|
| 1 | Critical | **Fixed** | `--extra cuda`/`cpu` now routed to real indexes | `start.sh`, `start.ps1`, `pyproject.toml` |
| 2 | Critical | **Fixed** | `test_journalService.py` rewritten | `tests/services/test_journalService.py` |
| 3 | Moderate | **Fixed** | `ColoredFormatter` dead code removed | `app/logging_config.py` |
| 4 | Moderate | Open | `ChatMessage.role` naming inverted | `database/models.py`, `services/generation.py` |
| 5 | Moderate | Open | `start.ps1` lowercase `frontend` path | `start.ps1` |
| 6 | Minor | Partially fixed | `ragas`/`rapidfuzz` still unused (`strip-markdown` now used) | `pyproject.toml` |
| 7 | Minor | Open | `rag.py` `__getattr__` facade is fragile | `services/rag.py` |
| 8 | Minor | Partially fixed | Device now validated; model/language still cached at init | `services/transcription.py` |
| 9 | Critical | **Fixed** | CUDA torch index URL now configured | `pyproject.toml` |
| 10 | Minor | Open | ChromaDB collection name hardcoded, no versioning | `services/chroma.py` |
| 11 | Moderate | Open | Path A tag extraction (`/extract-tags`) unused by UI | `routes/query.py`, `services/tagService.py`, `lib/api.ts` |
| 12 | Moderate | Open (pinned by xfail) | Manual edits don't refresh `derived_meta` provenance | `repositories/sourceRepository.py` |
| 13 | Minor | Open | ≥6 unused `Frontend/lib/api.ts` client functions | `lib/api.ts` |
| 14 | Minor | Open | Device-availability detection implemented 3× | `start.sh`, `start.ps1`, `settings_service.py`, `routes/settings.py` |
| 15 | Minor | Open (pinned, no fix decided) | Confirmed LLM tag indistinguishable from manual | `routes/tags.py`, `repositories/tagRepository.py` |
| 16 | Minor | **Fixed** (this doc pass) | `HANDOVER.md` pipeline/testing sections were stale | `docs/HANDOVER.md` |
| 17 | Minor | Open (confirmed, harmless on SQLite today) | Schema/migration drift on 4 columns | `database/models.py`, `migrations/versions/` |
| 18 | Moderate | **Fixed** | Checkbox tick raced against `startReflection`'s deselect-all reset | `hooks/useChatManagement.ts`, `app/page.tsx` |
| 19 | Moderate | **Fixed** | Llama Guard S6 false-positived the support card on ordinary conversation | `services/safety.py` |
| 20 | Moderate | **Fixed** | Update failures could discard an already-successful reply (3 call sites) | `services/reflectionLoop.py`, `routes/query.py`, `services/generation_registry.py` |
| 21 | Minor | Open (unconfirmed, no repro) | Three poll loops; one merge path's `content` overwrite is an unconfirmed watch item | `hooks/useChatManagement.ts`, `hooks/useSourceManagement.ts` |
| 22 | Minor | **Fixed** | Same poll loops flooded uvicorn access logs with noise; also polled while tabs were backgrounded | `app/logging_config.py`, `hooks/useChatManagement.ts`, `hooks/useSourceManagement.ts` |
| 23 | Moderate | Open (needs live verification) | `start.sh` port-8000 auto-recovery only fixture-tested, not verified against a real leftover backend | `start.sh` |
