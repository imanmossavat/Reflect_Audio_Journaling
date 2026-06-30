# REFLECT — Developer Handover Document

> **Scope**: Backend (`Backend/app/**`, `Backend/database/models.py`, `Backend/start_backend.py`), startup scripts, `Backend/pyproject.toml`, Frontend (`Frontend/app/**`, `Frontend/components/**` excluding shadcn/ui stock, `Frontend/hooks/**`, `Frontend/lib/**`, `Frontend/context/**`), and `Backend/tests/**`.
> **Date produced**: 2026-06-30

---

## 1. What the product is

REFLECT is a **fully private, local-first AI audio journal**. There is no cloud backend, no data leaves the machine, and all AI inference runs via Ollama using open-weights models. Users record or upload audio (and text) journal entries, which are automatically transcribed, chunked, embedded, and indexed for semantic search. A chat interface lets users ask questions grounded in their journal entries, and a guided reflection mode walks them through the six-stage **Gibbs Reflective Cycle**.

**Key constraints the architecture is built around:**
- SQLite + Chroma run on the same machine as the user; no remote DB.
- Ollama must be running locally; model availability is checked at every LLM call.
- HTTPS is required for microphone access in browsers (handled by mkcert in the startup scripts).
- WhisperX is the transcription engine — it is heavy (~1.5 GB download) and GPU-optional.

---

## 2. System requirements and startup

| Requirement | Value |
|---|---|
| Python | 3.11 exactly (pinned in `pyproject.toml`) |
| Node.js | LTS (installed by `start.sh` via fnm) |
| RAM | 16 GB minimum |
| Disk | ~20 GB (models + venv + Chroma) |
| Ollama | Must be installed and running; needs `gemma4:e4b` and `nomic-embed-text` pulled |

### Startup flow (`start.sh` / `start.ps1`)

1. Installs `uv` (Python package manager) if missing.
2. Installs Node.js via `fnm` (Mac/Linux) or `winget` (Windows) if missing.
3. Installs `mkcert`, generates TLS certs for `localhost` + all LAN IPs into `certs/`. Re-runs detect if the current IP is not already in the cert's SAN list and regenerate if needed.
4. Detects NVIDIA GPU via `nvidia-smi`; selects `--extra cuda` (CUDA PyTorch) or `--extra ml` / `--extra cpu` (CPU PyTorch).
5. Runs `alembic upgrade head` to apply any pending DB migrations.
6. Starts `python start_backend.py` (FastAPI on port 8000) in the background.
7. Runs `npm ci` and starts the Next.js frontend (`npm run dev:tls` if TLS certs exist, else `npm run dev`).

**Windows quirk**: The PS1 script also downloads FFmpeg 7 shared DLLs from BtbN's releases and drops them next to `libtorchcodec_core7.dll` so torchcodec can find them. The Bash script just relies on a system ffmpeg install.

`Backend/start_backend.py`: Detects whether TLS certs exist in `../certs/`; constructs the `uvicorn` command with or without `--ssl-certfile` / `--ssl-keyfile`; prints local + LAN URLs before launching.

---

## 3. Repository layout

```
Reflect_Audio_Journaling/
├── Backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app + lifespan
│   │   ├── config.py             # Settings proxy (reads from settings_service)
│   │   ├── db.py                 # SQLite session factory
│   │   ├── logging_config.py     # Single dictConfig setup; logger = getLogger("reflect")
│   │   ├── routes/               # FastAPI routers (source, query, chat, tags, settings)
│   │   ├── services/             # Business logic
│   │   ├── repositories/         # DB CRUD (sourceRepository, chatRepository, tagRepository)
│   │   ├── schemas/              # Pydantic request/response models
│   │   ├── prompts/              # LLM prompt strings (production + legacy)
│   │   └── utils/                # html_text, markdown_html, filename_dates, unique_path
│   ├── database/
│   │   ├── models.py             # All SQLModel table definitions
│   │   ├── database.db           # SQLite DB (runtime, not committed)
│   │   ├── chroma/               # ChromaDB persistent store (runtime, not committed)
│   │   └── inbox/                # File watcher drop folder
│   ├── data/
│   │   ├── settings.json         # User settings (runtime, not committed)
│   │   └── .welcome_seeded       # Sentinel: welcome note has been inserted
│   ├── migrations/               # Alembic; versions/ has migration files (don't read each)
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── services/             # test_journalService.py (stale), test_rag_retrieval.py, test_ranking.py, test_reranker.py, test_temporal.py
│   │   └── utils/                # test_filename_dates.py, test_unique_path.py
│   ├── logs/                     # app.log (runtime)
│   ├── pyproject.toml
│   └── start_backend.py
├── Frontend/
│   ├── app/                      # Next.js App Router pages
│   ├── components/               # React components (UI stock in components/ui/ — skip)
│   ├── hooks/                    # useSourceManagement, useChatManagement, useSidebarResize
│   ├── lib/                      # api.ts (all backend calls), gibbs.ts, utils.ts
│   └── context/                  # generation-provider.tsx (SSE state)
├── certs/                        # mkcert TLS certs (runtime, not committed)
├── start.sh
├── start.ps1
└── README.md
```

---

## 4. Database schema

All tables live in `Backend/database/models.py` using **SQLModel** (Pydantic + SQLAlchemy ORM).

### Core tables

**`Source`** — the central entity. Represents one journal entry (audio, text, markdown, or a promoted chat transcript).

| Field | Type | Notes |
|---|---|---|
| `id` | int PK | |
| `filename` | str? | null for quick-text notes |
| `file_type` | str? | e.g. "audio/webm", "text/plain", "chat" |
| `file_path` | str? | absolute path on disk |
| `text` | str? | plain text for RAG/embeddings |
| `text_html` | str? | rich HTML for display (TipTap) |
| `transcript_segments` | JSON? | list of `{text, start_s, end_s}` for audio player sync |
| `summary` | str? | LLM-generated plain text |
| `summary_html` | str? | user-edited HTML (set only when user edits; LLM gen clears it) |
| `derived_meta` | JSON? | e.g. `{"summary_prompt_version": "v1"}` |
| `status` | str | see status lifecycle below |
| `created_at` | datetime | |
| `edited_at` | datetime | updated on any PATCH |

**Status lifecycle**: `not processed` → `queued` → `transcribing` → `chunking` → `indexing` → `processed`. Failure paths: `failed`, `failed_no_speech`, `failed_ollama_not_running`, `failed_ollama_not_installed`, `failed_ollama_model_missing`.

**`Chunk`** — one RAG chunk from a Source.
- `source_id` FK, `chunk_text`, `chunk_index`
- Stored in both SQLite (for reference) and ChromaDB (for vector search).

**`Tag`** — lowercase tag name. Many-to-many with Source via `SourceTag`.

**`SourceTag`** — junction with an `origin` field: `"llm"` (auto-extracted) or `"user"` (manually added). This distinction lets the system recompute LLM tags without destroying user-added ones.

**`Question` / `Answer`** — legacy Q&A pairs saved via `/save-answer`. Not central to current flows.

**`ScaleQuestion` / `ScaleResponse`** — Likert-style responses (used in Gibbs chat messages via `ChatMessage.scale_value`).

**`Chat`** — a conversation.
- `title`, `source_id` (FK to Source when promoted), `reflection_goal`, `reflection_scope` (JSON: `{topic, items, source_ids}`)

**`ChatMessage`** — one turn in a chat.
- `role`: `"question"` (facilitator/AI) or `"answer"` (user). **Note: the naming is inverted** — "question" is the assistant, "answer" is the human.
- `gibbs_step`: int 1–6 when the message belongs to a guided reflection stage.
- `sources`: JSON array of retrieved chunk references (for RAG answers).
- `thinking`, `model`: stored for provenance.

---

## 5. Backend architecture

### 5.1 FastAPI app (`Backend/app/main.py`)

Startup `lifespan` does three things:
1. Re-queues any sources stuck in transient statuses (`queued`, `transcribing`, `chunking`, `indexing`) — handles interrupted processing from a prior crash.
2. Seeds a welcome note on a fresh database (guarded by `Backend/data/.welcome_seeded` sentinel).
3. Starts a Watchdog file observer on `Backend/database/inbox/`.

CORS is `allow_origins=["*"]` — intentional, since this is a local-only app.

### 5.2 Request processing pipeline

A new audio or text source goes through this pipeline (orchestrated in `sourceService._process_source_sync()`):

```
Upload → save file to disk → set status "queued"
  → (if audio + no text) Transcribe (WhisperX) → set status "transcribing" → update transcript
  → Chunk (spaCy / day-split / LLM fallback) → set status "chunking"
  → Index (LlamaIndex → ChromaDB embed via nomic-embed-text) → set status "indexing"
  → set status "processed" → extract+store tags (LLM) → generate summary (LLM)
```

**SQLite concurrency note**: Each DB write in the pipeline opens and immediately closes its own short-lived session. This avoids holding the SQLite write lock during the long transcription and LLM calls.

### 5.3 Transcription (`services/transcription.py`)

`TranscriptionManager` is instantiated once at startup and held in memory. It is heavy (~1.5 GB):
- Loads WhisperX ASR model (Whisper backbone, configurable: tiny/base/small/medium/large-v3).
- Loads a language-specific alignment model (pyannote-audio).

Pipeline: `ffmpeg` (via `imageio_ffmpeg`) decodes audio to 16kHz mono int16 PCM → numpy float32 → WhisperX ASR → WhisperX alignment → extracts `words` (timestamps) and `sentences` (segments). If the detected language differs from the pre-loaded alignment model's language, it hot-swaps the alignment model.

### 5.4 Chunking (`services/chunking.py`)

Three-tier strategy applied in order:

1. **Day-split**: regex on day-of-week labels (Monday, Tuesday, …) — good for daily journal entries.
2. **spaCy sentence chunker**: respects sentence boundaries; max ~500 chars per chunk. Model cached per language in `_nlp_cache`.
3. **LLM fallback**: for single chunks > 1000 chars that spaCy couldn't split, calls Ollama in JSON grammar-constrained mode.

### 5.5 RAG retrieval (`services/retrieval.py`, `services/ranking.py`, `services/reranker.py`)

Full pipeline in `ranked_retrieve()`:

1. **Temporal filter**: `parse_temporal_range()` extracts date phrases from the query (today, last week, last 3 months, named months, etc.) → `get_source_ids_in_range()` → `MetadataFilter(IN)` on ChromaDB.
2. **Tag filter**: `get_sources_by_tags()` → `MetadataFilter(IN)`. Supports ANY (OR) or ALL (AND) matching.
3. **Pool**: over-sample `pool_k = max(top_k × 4, 20)` candidates from ChromaDB.
4. **Backfill**: if the filtered pool is < `top_k` and `allow_backfill=True`, supplements with unfiltered hits.
5. **Cross-encoder rerank**: `BAAI/bge-reranker-v2-m3` (Apache 2.0, multilingual) sigmoid-scores each candidate.
6. **Temporal score blend**: `recency_decay()` with `HALF_LIFE_DAYS=90`; blended as `relevance×1.0 + temporal×0.3`.
7. **Top-k slice** and return.

### 5.6 Generation (`services/generation.py`, `services/generation_registry.py`)

**Query/chat path** (`generation_registry`):

- `_jobs: dict[int, GenerationJob]` keyed by `chat_id`. One job per chat.
- `GenerationJob` holds an SSE **replay buffer** so reconnecting clients (browser refresh, navigation away and back) get all events from the start of the generation.
- `generation_lock = asyncio.Semaphore(1)` (`ollama_gate.py`) serialises all LLM generation calls globally.
- Full pipeline per job: Ollama health check → model check → safety guard check (is llama-guard3:1b installed?) → **input guardrail** → condense question (rewrite follow-ups as standalone) → retrieve → stream generate → **output guardrail** → persist message → emit `done`.
- Terminal SSE event types: `done`, `error`, `idle`, `fallback`, `guard_unavailable`.
- Jobs linger 30 s after finishing so a reconnect can still replay the completed stream.

**Gibbs facilitator path** (`routes/query.py → /generate-question`):

- Separate streaming path, **not** using the generation registry. Direct `AsyncClient` Ollama call, streamed SSE.
- Safety guard wraps the generated question before it reaches the client.

### 5.7 Safety (`services/safety.py`)

Wraps **Llama Guard 3 (1b)** via Ollama. Two entry points:

- `classify_user_text()` — screens the user's input before it reaches the LLM.
- `classify_ai_text()` — screens the LLM's output before it reaches the user.

**Fail-open design**: any error (model missing, Ollama down, timeout) returns `_SAFE` and never blocks journaling. This is intentional — the privacy of journaling takes precedence over guard coverage. The `guard_unavailable` SSE event is emitted to the client so it can prompt the user to install the guard model.

Categories mapped to `SafetyKind`:
- `S11` (suicide/self-harm) → `"self_harm"`
- `S1`, `S2`, `S6` (violence, CSAM, illegal activity) → `"support"`

When a hit occurs, the UI renders a dismissible **support card** in the chat thread — not a hard error.

### 5.8 Settings (`services/settings_service.py`)

Stored in `Backend/data/settings.json`. Thread-safe reads/writes via `threading.Lock` and atomic writes (`.json.tmp` + `os.replace`). Defaults:

| Setting | Default |
|---|---|
| `chat_model` | `gemma4:e4b` |
| `embed_model` | `nomic-embed-text` |
| `ollama_host` | `http://localhost:11434` |
| `device` | `cpu` |
| `whisper_model` | `base` |
| `language` | `en` |
| `safety_model` | `llama-guard3:1b` |
| `thinking_enabled` | `true` |
| `num_ctx` | `16384` |
| `theme` | `system` |
| `date_format` | `dmy` |

`on_change()` listener registration lets other services react to settings changes. `_validate()` enforces allowed values.

### 5.9 File watcher (`services/file_watcher.py`)

Watchdog observer on `database/inbox/`. On a new file:
1. Waits for file size to stabilise (3 rounds × 1 s) before treating it as fully written.
2. POSTs to `/source/uploadFile/processed`.
3. Moves the file to `inbox/done/` via `unique_path()` (appends ` (n)` suffix on collision).
4. Deduplication via `_inflight` set (thread-safe) prevents double-processing if events fire twice.

The mobile upload page (`/upload/raw`) and the drag-to-inbox endpoint (`/source/drop-to-inbox`) both feed this path.

### 5.10 Chat promotion (`services/chatService.py`)

`promote_chat()` serialises a `Chat` + its `ChatMessage` list to Markdown and creates a new `Source` with `file_type="chat"`. The source is then processed through the normal chunking/indexing pipeline, making the chat transcript searchable via RAG. `reindex_chat()` repeats this when the chat has new messages.

### 5.11 Tag system (`services/tagService.py`, `repositories/tagRepository.py`)

- `extract_and_store_tags()`: calls LLM with grammar-constrained JSON (3–6 tags, verbatim quotes) → clears existing `origin="llm"` tags → upserts new ones. **User tags are never touched.**
- `suggest_tags_via_llm()`: lighter chat-API variant returning `[{name, reason}]` for the user to confirm.
- `get_or_create_tag()`: normalises to lowercase; uses flush (not commit) for batch-safe upsert.

### 5.12 Summary generation (`services/summaryService.py`, `prompts/summary_prompt.py`)

One-paragraph, 1–3 sentences, neutral, third-person. Truncates input to 8000 chars. Prompt version tracked in `derived_meta.summary_prompt_version` for future comparison. When the user edits the summary in the UI, `summary_html` is set; when LLM regenerates, `summary_html` is cleared (only the plain `summary` field is set).

### 5.13 Temporal parsing (`services/temporal.py`)

Regex-based; no external dependency. Recognised phrases:
- `today`, `yesterday`
- `this week/month/year`, `last week/month/year`
- `last N days/weeks/months/years`
- `recently` / `lately` → soft 30-day window (recency decay only, no SQL filter)
- Named months (`january`, `february`, …) — "may" treated as month only when a year is also present (to avoid colliding with "may" as a modal verb)
- Bare 4-digit years

Returns `DateRange(start, end, hard=True/False)`. `hard=False` means only apply recency decay, don't filter by SQL date range.

---

## 6. Routes overview

| Router | Prefix | Key endpoints |
|---|---|---|
| `source.py` | `/source` | GET /sources, POST upload (raw/processed, file/text), PATCH /{id}, DELETE /{id}, POST /process/{id}, POST /{id}/summary/regenerate |
| `query.py` | `/` | POST /query (sync RAG), POST /query-stream (SSE), GET /chats/{id}/generation-stream (resume SSE), GET /generations, POST /generate-question (Gibbs SSE), POST /reflection/topics, POST /safety/check, POST /extract-tags, POST /save-answer |
| `chat.py` | `/chats` | CRUD + POST /{id}/messages, POST /{id}/promote, POST /{id}/reindex |
| `tags.py` | `/tags` | GET /all, GET /all-with-sources, GET /{source_id}, POST /{source_id}, POST /{source_id}/suggest/confirm, DELETE /{source_id}/{tag_id}, GET /{source_id}/suggest |
| `settings.py` | `/settings` | GET/PUT /settings, GET /settings/devices, GET /settings/ollama-models, GET /settings/spacy-models |

---

## 7. SSE streaming protocol

Two SSE streams are used:

### Chat generation stream (`/query-stream`, `/chats/{id}/generation-stream`)

Events (JSON objects in `data:` lines):

| `type` | Payload fields | Meaning |
|---|---|---|
| `stage` | `name`, `count?` | Pipeline stage (checking, queued, searching, retrieved, thinking, writing) |
| `progress` | `chars` | Cumulative generated character count (for skeleton UI) |
| `sources` | `sources[]` | Retrieved chunks that ground the answer |
| `done` | `model`, `message_id` | Answer complete; message persisted |
| `fallback` | `kind` | Guard tripped; show support card instead of answer |
| `guard_unavailable` | `model`, `command` | Guard model not installed; show setup card |
| `error` | `detail` | Fatal error |
| `idle` | — | No generation active (reconnect to a finished job) |

### Question generation stream (`/generate-question`)

Simpler SSE format:
- `{"progress": N}` — character count
- `{"text": "..."}` — final question text (after guard clears)
- `{"fallback": "self_harm"|"support"}` — guard tripped
- `[DONE]` — terminal sentinel

---

## 8. Frontend architecture

**Stack**: Next.js 16 / React 19, TypeScript, Tailwind CSS v4, shadcn/ui (Radix UI).

### Key pages

| Page | Path | Purpose |
|---|---|---|
| Main workspace | `/` (`app/page.tsx`) | Three-pane layout: source list, chat/note/graph, tools panel |
| Source detail | `/sources/[id]` | TipTap editors for transcript + summary, audio player, tags, retry |
| Settings | `/settings` | Model picker, Ollama config, device, Whisper, date format, theme |
| Account | `/account` | Activity calendar, stats, profile name, privacy tab |
| Graph | `/graph` | Full-screen knowledge graph |
| Mobile upload | `/upload/raw` | Recording, file upload, text note for mobile/remote capture |

### State management

All significant state lives in **hooks** consumed by `app/page.tsx`:

- **`useSourceManagement`**: sources list, upload flows (text/file/recording), processing polling (2.5 s interval while any source is processing, 5 s interval for new sources), tag hydration after processing completes.
- **`useChatManagement`**: chats list (5 s poll), active chat + messages, Gibbs state machine, message submission, chat rename/delete/promote.
- **`useSidebarResize`**: left/right sidebar widths with localStorage persistence; collapse/expand toggles.
- **`GenerationProvider`** (`context/generation-provider.tsx`): global SSE streaming state. On mount, calls `/generations` and reconnects to any in-flight jobs. `startTextGeneration()` initiates a new stream. `generationFor(chatId)` returns a `StreamingAssistant | null`. Finished entries linger 2 s then auto-clear.

### Recording state machine

`useSourceManagement` implements: `idle → recording ⇄ paused`. Pausing drops into a review screen (audio preview). Saving from review calls `MediaRecorder.stop()` and uploads the finalised blob. The `onstop` handler checks `uploadPendingRef` to distinguish a user-requested upload from a cancel/close (which should discard the audio).

### Gibbs state machine (`useChatManagement`)

```
startReflection() → setup phase (gibbsSetup=true, sources deselected)
  ↓ user picks sources + writes goal
beginReflection() → persist goal/scope on Chat → generateGibbsQuestion(step=1, mode="deep_dive")
  ↓ user answers each question
advanceGibbsStep() → step++ → generateGibbsQuestion(next, "deep_dive")
  ...up to step 6...
  ↓ step 6 complete
setGibbsComplete(true) → wrap-up panel shown
  ↓ user clicks "New cycle"
beginNewCycle() → resetChatState() → startReflection()
```

`askClarifying()` re-calls `generateGibbsQuestion(currentStep, "clarifying")` without advancing.

`handleSelectGibbsStep()` lets the user jump to any step, regenerating the question.

When loading a chat that has Gibbs messages (tagged with `gibbs_step`), the hook restores the Gibbs state from the message history and resumes at the furthest stage reached.

### API client (`lib/api.ts`)

All backend calls go through `api.*` functions in `Frontend/lib/api.ts`. Key design points:

- `getBackendBaseUrl()`: respects `NEXT_PUBLIC_BACKEND_URL` env var; otherwise mirrors the frontend's protocol and hostname with port 8000 (so HTTPS frontend → HTTPS backend automatically).
- `withTimeout(ms)`: wraps every `fetch` with an `AbortController` timeout (default 20 s; long ops like transcription/summary get 600 s).
- `request<T>()`: shared fetch wrapper; parses FastAPI's `{"detail": "..."}` error format.
- `consumeChatStream()`: shared SSE parser used by both `streamQuery` (POST) and `subscribeGeneration` (GET resume). Splits on `\r?\n\r?\n` event boundaries.

### Text/HTML duality

Every rich-text source has both `text` (plain, for RAG/embeddings/tags) and `text_html` (for TipTap display). The plain text is always **derived** from the HTML via `html_to_text()`, never edited independently. This prevents drift between what the user sees and what the AI searches. When the TipTap editor saves `text_html`, the backend re-derives `text` from it.

---

## 9. Key design decisions

### SQLite concurrency
Each DB write in the processing pipeline opens and immediately closes its own short-lived session. This avoids holding SQLite's write lock during transcription (~seconds to minutes) or LLM calls (seconds to tens of seconds). The `_process_source_sync()` function deliberately interleaves session.close() with long-running operations.

### Generation resilience (replay buffer)
`GenerationJob` in `generation_registry.py` keeps an SSE event replay buffer server-side. When the browser navigates away mid-generation and returns, it reconnects to the same job (via `/chats/{id}/generation-stream`) and replays all events from the start. `GenerationProvider` calls `/generations` on mount and auto-reconnects to any in-flight jobs.

### Tag origin tracking
`SourceTag.origin` (`"llm"` or `"user"`) allows LLM tags to be recomputed at any time without touching user-added tags. `clear_llm_tags_for_source()` only removes `origin="llm"` junction rows.

### Fail-open safety
Safety guardrails never block journaling. Any error from llama-guard3:1b returns `_SAFE`. The `guard_unavailable` SSE event is shown as an in-thread setup card, not a hard error. This is a deliberate trade-off prioritising journaling continuity over guardrail coverage.

### Prompts for RAG vs chat
`SYSTEM_PROMPT` includes an explicit anti-refusal clause and first-person voice guidance. `STRICT_REFUSAL_TEMPLATE` is kept as a comparison baseline (RAGAS accuracy ~0.467 vs 0.667 for the production prompt). `CONDENSE_TEMPLATE` rewrites follow-up questions into standalone queries before retrieval, with a fail-safe that returns the original on error.

### Scoring
Relevance score from BAAI/bge-reranker-v2-m3 (sigmoid-activated, range [0,1]) is blended with a temporal recency score (exponential decay, half-life 90 days, neutral 0.5 for undated sources) at ratio 1.0:0.3. Sources with no `created_at` get 0.5 (neutral) temporal score.

---

## 10. Testing

Tests live in `Backend/tests/`. Run with:

```bash
cd Backend
uv run --extra dev pytest
```

### Test files and status

| File | Status | Notes |
|---|---|---|
| `tests/services/test_journalService.py` | **Stale** | Tests reflect an older API. `index_chunks` is called with `journal_id` key (current uses `source_id`). `update_source_text` no longer exists as a public function. `process_source` behaviour changed (now just queues; background task handles processing). These tests will fail against current code. |
| `tests/services/test_rag_retrieval.py` | Up to date | Monkeypatches `retrieval` module directly (correct after `rag.py` refactor). Tests temporal filter, backfill, non-temporal skip, top_k slicing, identity reranker injection. |
| `tests/services/test_ranking.py` | Up to date | Tests `recency_decay`, `combined_score`, `score_candidates` with parametrized cases. |
| `tests/services/test_reranker.py` | Up to date | Stubs `_model()` to avoid downloading weights. Tests empty input and score pass-through. |
| `tests/services/test_temporal.py` | Up to date | Comprehensive parametrized tests for all temporal phrase types. Fixed `NOW=2026-06-03 12:00`. |
| `tests/utils/test_filename_dates.py` | Up to date | Year-first, dmy/mdy format, no-silent-swap, no-date parametrized cases. |
| `tests/utils/test_unique_path.py` | Up to date | No collision, single, double collision, basename-only (path traversal) cases. |

`conftest.py` adds `Backend/` to `sys.path` so imports work without installing the package.

---

## 11. Legacy code

Several files in `Backend/app/prompts/` are no longer used in the production flow but are kept for reference:

| File | Status |
|---|---|
| `question_prompt.py` | Legacy — `build_prompt()` used by old Q&A flow |
| `dictionary_question_prompt.py` | Legacy — `build_messages()` with elaborate rules, forced assistant prefix |
| `simpler_dictionary_question_prompt.py` | Legacy — simplified `build_messages()`, keeps last 2 history pairs |
| `segment_prompt.py` | Legacy — character-index-based segmentation prompt |

`rag.py` is a back-compat facade that re-exports everything from `prompt.py`, `llm_runtime.py`, `retrieval.py`, and `generation.py` via `__getattr__`. Import `from app.services.rag import X` still works but routes to the real module.

---

## 12. Things to watch out for

1. **`test_journalService.py` is stale.** Running it will fail. The tests reference `update_source_text`, `process_source` (old sync behaviour), and `index_chunks(journal_id=...)`. These need to be rewritten against the current `sourceService` API before you can trust CI.

2. **`ChatMessage.role` naming is inverted.** `"question"` means the AI/facilitator spoke; `"answer"` means the human spoke. This is a historical naming accident. `generation.py`'s `to_chat_messages()` maps `"answer"` → `role: "user"` and `"question"` → `role: "assistant"` when building the Ollama context window.

3. **WhisperX loads on first transcription request**, not at import time (despite `TranscriptionManager.__init__` loading models). The manager itself is only instantiated when the first transcription is needed. This means the first audio upload will have a noticeable delay while models load (~10–30 s depending on hardware).

4. **ChromaDB collection name is hardcoded** as `"source_chunks"` in `chroma.py`. If you need to reset the vector store, delete `Backend/database/chroma/` entirely and re-process all sources.

5. **The `rag.py` facade's `__getattr__`** provides dynamic `OLLAMA_BASE_URL`, `EMBED_MODEL`, `LLM_MODEL` attributes for backward compatibility. If you add a new attribute to any of the sub-modules and expect it to be accessible via `from app.services.rag import X`, add it to `rag.py`'s explicit re-exports or the `__getattr__` fallback.

6. **Alembic migrations are in `Backend/migrations/versions/`**. Never edit a migration that has already been applied. If you change `models.py`, generate a new migration with `uv run alembic revision --autogenerate -m "description"` and review it before committing.

7. **Settings are not reloaded on the fly for Whisper/spaCy.** Changing the Whisper model or language in Settings takes effect on the next transcription (the `TranscriptionManager` is re-instantiated lazily when settings change, because `config.py` reads from `settings_service` which calls `on_change()` listeners).

8. **`pyproject.toml` has no `cuda` extra** — the Windows script uses `--extra cpu` and the Mac/Linux script uses `--extra ml` for CPU. The `cuda` name used in `start.sh` (`TORCH_EXTRA="cuda"`) when an NVIDIA GPU is detected maps to the `cuda` extra which is **not currently defined** in `pyproject.toml` (only `ml` and `dev` are). This means CUDA builds on Mac/Linux currently fall back to the `ml` (CPU torch) extra. Worth fixing if GPU support is a priority.

---

## 13. Gibbs Reflective Cycle — implementation notes

The six stages are:

| Step | Key | Label | Purpose |
|---|---|---|---|
| 1 | description | Description | The concrete moment or situation |
| 2 | feelings | Feelings | What the user felt |
| 3 | evaluation | Evaluation | What went well and what was hard |
| 4 | analysis | Analysis | Patterns noticed |
| 5 | conclusion | Conclusion | Insights emerging |
| 6 | actionPlan | Action Plan | What to explore or try next |

The facilitator prompt (`Backend/app/prompts/gibbs_facilitator_prompt.py`) has three actions: `open` (stage intro), `clarify` (stay in stage), `reply` (acknowledge + invite/advance). Stage 6 gets a softening note not to pressure users to invent concrete action plans.

The facilitator is grounded in up to 2000 chars of the user's included sources (concatenated plain text) and receives the last 8 turns of conversation history as `{question, answer}` pairs.

Frontend state: `gibbsActive`, `gibbsSetup`, `gibbsStep`, `gibbsComplete`, `gibbsGoal`, `gibbsScopeItems` live in `useChatManagement`. They are **ephemeral** (not persisted between page loads) except for `reflection_goal` and `reflection_scope` which are saved on the Chat row. On load, the hook detects Gibbs messages (by `gibbs_step` field) and restores the active state.

---

## 14. Adding a new feature — checklist

**New source type:**
- Add a file extension to `useSourceManagement.ts`'s `allowedUploadExtensions`.
- Add `file_type` handling in `mapSourceType()`.
- If it needs new processing, add a branch in `sourceService._process_source_sync()`.

**New LLM prompt:**
- Add the prompt string in `Backend/app/prompts/`.
- Wire it through the relevant service.
- If it uses grammar-constrained JSON, define the JSON schema in the same file (see `tag_extraction_prompt.py` for the pattern).

**New settings field:**
- Add the field to `_Settings` in `settings_service.py` with a default.
- Add it to `AppSettings` interface in `Frontend/lib/api.ts`.
- Add it to the Settings page in `Frontend/app/settings/page.tsx`.
- Add `_validate()` entry if the field has constrained values.

**New database column:**
- Add the field to the relevant SQLModel table in `models.py`.
- Generate an Alembic migration: `uv run alembic revision --autogenerate -m "add column X"`.
- Review the generated migration before committing.

**New API endpoint:**
- Add to the appropriate router in `Backend/app/routes/`.
- Add the typed call to `Frontend/lib/api.ts`.

---

## 15. Environment variables

| Variable | Used in | Default |
|---|---|---|
| `NEXT_PUBLIC_BACKEND_URL` | `Frontend/lib/api.ts` | Auto-derived from window.location |
| `NEXT_PUBLIC_BACKEND_PORT` | `Frontend/lib/api.ts` | `8000` |

The backend reads no environment variables directly; all configuration is in `Backend/data/settings.json` managed by `settings_service.py`.
