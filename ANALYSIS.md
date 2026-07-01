# Implementation Roadmap

**Date:** June 2026

This document describes the current state of each subsystem, the target behaviour, the concrete engineering tasks required to reach it, and the expected outcome. It is intended as a working guide for the student and as a shared reference between the student and the supervisor.

---

## 2.1 Session State Management

**Current implementation**

- Gibbs session state (current stage, active flag, step counter) is held in frontend React `useState` and `useRef` hooks in `useChatManagement.ts`.
- On application load, `activeChatId` is restored from `localStorage` using the key `"reflect.activeChatId"`. If the restored chat contains Gibbs messages, `gibbsActive` is reconstructed as `true`.
- There is no server-side record of which stage a session is in. If the user closes the browser mid-session, stage progress cannot be recovered.
- Starting a new reflection does not explicitly clear the previous session from `localStorage`, which can result in the previous session being reloaded on the next open.

**Target implementation**

- Session state is persisted on the backend as a versioned JSON document associated with a unique session identifier (`session_id`).
- Each state write increments the version counter. Prior versions remain on disk and can be loaded for debugging or rollback.
- State updates are validated with Pydantic before being written. An invalid update leaves the prior version untouched.
- Session state is loaded from the backend explicitly at the start of each turn. It is not reconstructed from message history.
- Starting a new reflection creates a new `session_id` on the backend and clears the frontend's reference to any prior session.

**Implementation tasks**

- Create a `SessionState` Pydantic model covering: `session_id`, `version`, `current_stage`, `completed_stages`, `stage_ready`, `turns_in_stage`, `facts`, `open_questions`, `goal`, `context`, `last_turn_summary`, `session_complete`.
- Add backend endpoints: `POST /session/create`, `GET /session/{id}`, `PATCH /session/{id}` (accepts a delta, validates, writes new version).
- Write state to disk as `{session_id}_v{n}.json` in a `sessions/` directory after each turn.
- In `beginReflection()` on the frontend, call `POST /session/create`, store the returned `session_id`, and clear `ACTIVE_CHAT_STORAGE_KEY` from `localStorage`.
- Load session state at the start of each Gibbs turn from the backend rather than from React state.

**Expected outcome**

- Consistent session behaviour across browser reloads and machine restarts.
- No regression to a previous session when starting a new reflection.
- Full session history available for debugging and for generating the final reflection document.

---

## 2.2 Thin-Turn Handling

**Current implementation**

- Every user message is forwarded to the LLM with the full assembled context, regardless of content length or substance.
- Messages such as "okay", "hmm", or "not sure" receive the same treatment as a substantive multi-sentence response.
- The Gibbs prompt in `gibbs_facilitator_prompt.py` does not contain instructions for handling short or uninformative input.
- Extended thinking is enabled on the generation call. When the model receives a short message alongside a long context, it reasons at length and produces a disproportionately verbose response.

**Target implementation**

- Before calling the LLM, the backend classifies the incoming message as either a substantive turn or a thin turn.
- On a thin turn, the generation call still runs, but the prompt contains explicit fallback instructions directing the model to ask a single open question rather than reason over the full context.
- The extraction call (see 2.5 in the baseline design) is skipped on thin turns. A fallback summary is written to session state in code.
- Thin-turn classification is done in Python, not by the model.

**Implementation tasks**

- Implement `is_thin_turn(user_message: str) -> bool` in the backend. A turn is thin if the normalised message matches a known low-information set (`"ok"`, `"yes"`, `"no"`, `"maybe"`, `"idk"`, `"i don't know"`, `"not sure"`, `"hmm"`, etc.) or if the word count is three or fewer.
- Add a `## Handling short responses` section to the Gibbs facilitator prompt specifying that on a short or unclear message the model should ask exactly one open question and not advance the stage.
- Skip the extraction call and write a fallback `last_turn_summary` in code when `is_thin_turn` returns `True`.

**Expected outcome**

- Short acknowledgements no longer trigger lengthy LLM reasoning.
- The session continues coherently after a thin turn; the next question invites elaboration.
- Reduced latency and token cost on uninformative turns.

---

## 2.3 Response Streaming and Prompt Leakage

**Current implementation**

- The backend streams generation output to the frontend via SSE.
- Extended thinking is enabled on the generation call. Internal reasoning blocks produced by the model can appear in the streamed output if they are not explicitly filtered before forwarding.
- Structured metadata (`derived_meta`) attached to the generation response is not stripped before forwarding to the client.
- Prompt leakage has been observed in production: internal prompt structure and chain-of-thought content has appeared in the user-facing output. This was noted in June 2026 and had been seen previously without a fix being applied.

**Target implementation**

- The SSE stream forwarded to the frontend contains only `content` chunks with role `assistant`.
- Any `thinking`, `tool_use`, or `metadata` blocks produced by the model are consumed internally and never forwarded as SSE events.
- `derived_meta` and any other internal annotations are stripped at the stream boundary before the event is emitted.

**Implementation tasks**

- In the SSE generation pipeline, add a filter step that inspects each chunk before emitting it. Pass through only chunks where `type == "content_block_delta"` and the associated block is a text block with role `assistant`.
- Explicitly drop chunks of type `thinking_block_delta` and any event carrying `derived_meta` or similar internal keys.
- Add a test that calls the Gibbs generation endpoint with a standard prompt and asserts that the raw SSE event stream contains no content matching known prompt template strings (e.g., the string `"You are a reflective facilitator"`).

**Expected outcome**

- Internal prompt structure is never visible in the user interface.
- The streamed output is guaranteed to contain only model-generated facilitation text.
- The fix is verified by a test so that it cannot regress silently.

---

## 2.4 Environment and Cross-Machine Reproducibility

**Current implementation**

- `start.sh` detects an NVIDIA GPU and calls `uv sync --extra cuda`; otherwise it calls `uv sync --extra ml`. The `cuda` extra does not exist in `pyproject.toml`. Only `ml` and `dev` are defined.
- `start.ps1` calls `uv sync --extra cpu` by default and `uv sync --extra cuda` on GPU machines. Neither `cpu` nor `cuda` exists in `pyproject.toml`.
- On machines where conda is active alongside uv, the two environments can interact through PATH. The backend may run under the wrong Python interpreter, producing dependency mismatches.
- `transcription.py` resolves the ffmpeg binary at module import time using `imageio_ffmpeg.get_ffmpeg_exe()`. On Mac arm64 this downloads a platform-specific binary that has behaved differently across runs.
- The file watcher checks for `localhost+1.pem` to decide whether to use HTTPS when uploading processed files. The backend generates and uses `localhost.pem`. On machines where only the latter exists, the watcher falls back to HTTP while the backend requires HTTPS, causing `Connection reset by peer`.

**Target implementation**

- All four startup paths (`start.sh` CPU, `start.sh` GPU, `start.ps1` CPU, `start.ps1` GPU) reference extras that exist in `pyproject.toml`.
- The ffmpeg binary is resolved at transcription time by preferring the system `ffmpeg` on PATH and falling back to `imageio_ffmpeg` only if no system binary is found.
- The watcher uses the same certificate filename as the backend, or reads the filename from a shared environment variable.
- Setup documentation explicitly states that conda must not be active when running the start scripts.

**Implementation tasks**

- In `pyproject.toml`, add `cpu = ["torch==2.8.*", "torchaudio==2.8.*"]` and `cuda = ["torch==2.8.*+cu124", "torchaudio==2.8.*+cu124"]` extras with the appropriate index URLs, or rename the references in `start.sh` and `start.ps1` to use `ml` for CPU and define a separate CUDA variant.
- In `transcription.py`, replace `ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()` with `ffmpeg_exe = shutil.which("ffmpeg") or imageio_ffmpeg.get_ffmpeg_exe()`.
- Change the watcher's TLS detection to check for `localhost.pem` (the name `start.sh` generates) rather than `localhost+1.pem`, or introduce a `UPLOAD_URL` environment variable set by the start script.
- Add a note to `HANDOVER.md` under Environment Setup: "Run `conda deactivate` before running `start.sh`. Do not activate conda inside the project shell."

**Expected outcome**

- `uv sync` succeeds with the correct extra on all four startup paths.
- The backend runs under the Python 3.11 interpreter managed by uv on all platforms.
- The watcher and backend agree on TLS protocol, eliminating the connection reset error.
- Behaviour on Mac and Windows is reproducible from the same codebase.

---

## 2.5 Safety Guard

**Current implementation**

- Llama Guard 3 1b runs as a pre-flight check before each generation call.
- If the guard is unavailable (timeout, model not loaded, parse error), the system emits a `guard_unavailable` SSE event and continues with generation. This is a fail-open design.
- Llama Guard 3 1b has known category gaps and may not detect all harm categories reliably at the 1b scale.
- The distinction between "guard service is down" and "guard returned an error on a specific message" is not currently handled separately.

**Target implementation**

- Guard failures are distinguished by failure mode:
  - Guard service unavailable: emit `guard_unavailable`, continue with a user-visible notice.
  - Guard returned an error or inconclusive result on a specific message: block that message, return a safe refusal, and log the incident.
- The guard's known category limitations are documented so that advisors and users are aware of what it does and does not cover.

**Implementation tasks**

- In the guard invocation path, distinguish the `guard_unavailable` case (service not reachable) from a per-message error case (model returned an unexpected or unparseable result).
- For the per-message error case, return a blocked response rather than continuing to generation.
- Add a `SAFETY.md` note documenting the guard model, its known limitations at the 1b scale, and the categories it is expected to cover.

**Expected outcome**

- Guard failures on individual messages do not silently pass through to generation.
- Advisors have documented information about what the guard covers.
- The system behaves predictably under guard failure conditions.

---

## 2.6 Automatic Summary Generation

**Current implementation**

- Summary generation after source ingest requires manual triggering via a UI button.
- The `regenerate_summary()` endpoint exists and functions correctly.
- The initial project plan specified automatic summary generation per source on ingest as a Week 1 deliverable.

**Target implementation**

- After transcription completes and the transcript is persisted, summary generation is enqueued automatically as part of the same background processing job.
- The summary is available in the UI by the time the user opens the source, without requiring a manual trigger.

**Implementation tasks**

- In the post-transcription processing chain, add a call to `regenerate_summary()` (or equivalent) after the transcript is written to the database.
- Ensure the summary job runs in the same background worker as transcription so that failures are surfaced through the existing processing status mechanism.

**Expected outcome**

- Sources have summaries available immediately after processing completes.
- No manual action is required to generate a summary.
- The ingestion pillar matches the originally specified behaviour.

---

## 2.7 RAG Improvement Roadmap

**Current implementation**

- Retrieval uses dense vector search via ChromaDB with `nomic-embed-text` embeddings and a `BAAI/bge-reranker-v2-m3` cross-encoder reranker.
- There is no BM25 retrieval leg. Keyword-heavy queries for proper nouns, names, or specific dates are retrieved only if their embedding is close to the query embedding.
- Queries are sent to the retrieval pipeline as-is with no disambiguation, paraphrasing, or clarification step.
- RAGAS is listed as a dependency but no evaluation benchmark or evaluation script exists.
- Current retrieval accuracy is approximately 67%. The target is 95%.

**Target implementation**

- The RAG pipeline is split into independent, swappable modules: `retrieval.py`, `generation.py`, `prompt.py`, `evaluation.py`. Each module has a defined input/output interface and can be tested and replaced independently.
- Retrieval uses a hybrid approach combining dense vector search and BM25, with scores fused using Reciprocal Rank Fusion.
- Before answering a query, the system assesses whether the query is specific enough to answer with confidence. If not, it asks one clarifying question.
- A benchmark of 20–30 question-answer pairs covers the target use case. RAGAS is used to measure retrieval accuracy before and after each pipeline change.
- Model choices are documented: which model, why it was selected, what alternatives were considered.

**Implementation tasks**

- Create `retrieval.py`, `generation.py`, `prompt.py`, `evaluation.py` under `Backend/app/rag/`. Move the current `rag.py` logic into these files with clean interfaces.
- Build an evaluation script that loads the benchmark set and runs RAGAS against the current pipeline. Establish a baseline accuracy measurement.
- Classify the current ~33% of failures by type: retrieval failure, generation failure, instruction-following failure, or unanswerable question. Each type needs a different fix.
- Add a BM25 retrieval leg using `rank_bm25` or equivalent. Fuse BM25 and dense scores using RRF. Measure the change in accuracy against the benchmark.
- Add a clarification gate: before generating a final answer, have the model assess whether the query is specific enough. If not, return a clarifying question rather than an uncertain answer.
- Write `docs/model-choices.md` documenting the rationale for each model in the pipeline.

**Expected outcome**

- Each retrieval component can be modified or replaced without touching the rest of the pipeline.
- Accuracy improvement is measurable against a fixed benchmark.
- The clarification gate reduces confident-but-wrong answers.
- The supervisor can change prompts or retrieval logic by editing a single file.

---

## 2.8 Testing and Validation

**Current implementation**

- `Backend/tests/test_journalService.py` calls `journal_service.save_recording_to_db()`, which no longer exists. The test file fails on import.
- No other substantive tests exist for the Gibbs flow, the RAG pipeline, or the safety guard.
- There is no automated regression check running on the codebase.

**Target implementation**

- The test suite passes cleanly.
- Tests exist for the components with the highest instability risk: Gibbs stage transitions, RAG retrieval, and the safety guard.
- Each new module introduced as part of the RAG refactor has at least one test covering its input/output contract.

**Implementation tasks**

- Fix or delete `test_journalService.py`. If the tested behaviour still exists under a different API, update the call. If it does not, delete the test and add a note to `ISSUES.md` that the functionality was removed.
- Add a test for Gibbs stage advancement: given a session state at stage N with `stage_ready = True` and an advance-confirmation message, assert that the returned state is at stage N+1.
- Add a test for the thin-turn gate: given a message of "okay", assert that the extraction call is not made and that `last_turn_summary` contains the fallback string.
- Add a test for the safety guard: given a clearly safe message and a clearly harmful message, assert the expected guard outcomes.
- Add a smoke test for the RAG pipeline: given a known query and a seeded vector store, assert that the top-1 retrieved chunk contains the expected content.

**Expected outcome**

- The test suite runs without errors.
- Regressions in the Gibbs flow or the RAG pipeline are caught before they reach production.
- New contributors can verify that their changes do not break existing behaviour.

---

## Prioritized Implementation Roadmap

### Immediate — stop current breakage

| Task | File(s) | Effort |
|---|---|---|
| Fix `pyproject.toml` extras so `uv sync` succeeds on all platforms | `Backend/pyproject.toml`, `start.sh`, `start.ps1` | 1 hour |
| Fix TLS cert filename mismatch in the file watcher | File watcher config, `start.sh` | 30 minutes |
| Fix or delete the stale test in `test_journalService.py` | `Backend/tests/test_journalService.py` | 1 hour |
| Add fallback instructions to the Gibbs prompt and implement `is_thin_turn()` | `gibbs_facilitator_prompt.py`, new backend utility | 2–3 hours |
| Filter `thinking` blocks from the SSE stream | SSE generation pipeline | 2 hours |

### Next sprint — restore the design intent

| Task | File(s) | Effort |
|---|---|---|
| Implement backend session state persistence with versioned files | New `sessions/` module, new endpoints | 1–2 days |
| Separate `beginReflection()` from prior session state | `Frontend/hooks/useChatManagement.ts` | Half day |
| Re-enable automatic summary on ingest | Post-transcription processing chain | 2 hours |
| Add simple API key authentication to the backend | FastAPI dependency, `.env` | 2 hours |
| Distinguish guard-unavailable from per-message guard failure | Safety guard invocation path | 2 hours |

### Medium term — deliverables

| Task | File(s) | Effort |
|---|---|---|
| Create modular RAG pipeline (`retrieval.py`, `generation.py`, `prompt.py`, `evaluation.py`) | `Backend/app/rag/` | 2–3 days |
| Build evaluation benchmark and RAGAS harness | New `eval/` scripts | 1–2 days |
| Add BM25 retrieval leg with RRF fusion | `retrieval.py` | 1 day |
| Add clarification gate to the query flow | `generation.py`, `prompt.py` | 1 day |
| Write PII module design specification | New `docs/pii-spec.md` | 1 day |
| Write model choice documentation | New `docs/model-choices.md` | Half day |
| Add tests for Gibbs transitions, thin-turn gate, safety guard, RAG smoke test | `Backend/tests/` | 1–2 days |
