# Changes — June 2026

This file records every change made during the June 2026 fix session. It maps each change to the issue it resolves and the file(s) it touches.

---

## 1. Environment extras — `uv sync` no longer fails

**Issue:** `start.sh` called `uv sync --extra cuda` and `start.ps1` called `uv sync --extra cpu`. Neither `cuda` nor `cpu` existed as extras in `pyproject.toml`, so dependency installation was silently broken on every machine that did not already have a cached lock.

**Fix:**
- `Backend/pyproject.toml` — added `cpu` and `cuda` as explicit extras (both resolve to `torch==2.8.*`).
- `start.sh` — `TORCH_EXTRA` now defaults to `cpu` and switches to `cuda` on GPU machines. Both are valid.
- `start.ps1` — same change on Windows.

---

## 2. TLS certificate filename mismatch — file watcher HTTP/HTTPS confusion

**Issue:** The file watcher checked for `localhost+1.pem` to decide whether to use HTTPS. The backend generates `localhost.pem`. On machines where only `localhost.pem` existed, the watcher used HTTP while the backend required HTTPS, producing `Connection reset by peer`.

**Fix:**
- `Backend/app/services/file_watcher.py` line 17 — changed the existence check from `localhost+1.pem` / `localhost+1-key.pem` to `localhost.pem` / `localhost-key.pem`.

---

## 3. Configurable log level — logging can be turned on or off

**Issue:** Log level was hardcoded to `DEBUG`. There was no way to reduce verbosity in a demo or production-like run without editing code.

**Fix:**
- `Backend/app/logging_config.py` — reads `LOG_LEVEL` from the environment at startup. Defaults to `DEBUG`. Set `LOG_LEVEL=INFO`, `LOG_LEVEL=WARNING`, or `LOG_LEVEL=ERROR` to reduce console output. The file log (`logs/app.log`) always captures `DEBUG` regardless of the environment variable. Added `chromadb` and `watchdog` to the silenced third-party library list.

**Usage:**
```bash
LOG_LEVEL=INFO uv run python start_backend.py      # standard operational output
LOG_LEVEL=WARNING uv run python start_backend.py   # only warnings and errors
LOG_LEVEL=DEBUG uv run python start_backend.py     # full trace (default)
```

---

## 4. Additional debug logging throughout the pipeline

**Issue:** When something went wrong in the processing pipeline, generation, or safety guard, the logs did not give enough detail to diagnose the failure without adding print statements.

**Fix:**
- `Backend/app/services/file_watcher.py` — added `logger.debug` / `logger.info` / `logger.warning` at each step: file detected, waiting to stabilise, upload URL and TLS flag, response status code, move to done.
- `Backend/app/services/sourceService.py` — added `logger.debug` / `logger.info` at each pipeline stage: pipeline start, file type and path, transcription start and result, chunk count, indexing.
- `Backend/app/services/generation_registry.py` — added `logger.debug` for: model and thinking flag, history message count, condensed query, generation complete with answer/thinking length, output safety check start.
- `Backend/app/services/safety.py` — added `logger.debug` for classify call parameters and raw verdict; changed the exception handling to distinguish `TimeoutError` (logged at `ERROR`), `ConnectionError` (logged at `WARNING`), and unexpected exceptions (logged at `ERROR` with traceback).

---

## 5. Thin-turn handling — short responses no longer trigger long LLM reasoning

**Issue:** Messages like "okay", "hmm", or "not sure" were sent to the LLM with the full assembled context. With extended thinking enabled, the model reasoned at length over minimal input and produced disproportionately verbose responses.

**Fix:**
- `Backend/app/services/thin_turn.py` — new file. `is_thin_turn(text: str) -> bool` returns `True` when the message is empty, matches a known low-information phrase, or contains three words or fewer.
- `Backend/app/prompts/gibbs_facilitator_prompt.py` — added explicit fallback instructions to `GUIDELINES`: short/unclear responses get one open question; off-topic responses are briefly acknowledged then redirected; resistance is met with a simpler version of the current question; one question per response maximum.
- `Backend/app/routes/query.py` — in the `/generate-question` route, if the last user answer in `history` is thin and the requested action is `"reply"`, the action is overridden to `"clarify"`. Logged at `DEBUG`.

---

## 6. Safety guard — failure modes now distinguished in logs

**Issue:** All safety guard failures were caught by a single `except Exception` and logged at `WARNING`. There was no distinction between "Ollama is unreachable" (service-level problem) and "an unexpected error occurred on this specific message" (per-message problem worth investigating).

**Fix:**
- `Backend/app/services/safety.py` — split exception handling into three branches:
  - `asyncio.TimeoutError` — logged at `ERROR` (timeout on a reachable service is unexpected).
  - `ConnectionError` — logged at `WARNING` (Ollama not reachable; same as service-unavailable).
  - `Exception` — logged at `ERROR` with full traceback (`exc_info=True`).
  - Added `logger.debug` for the verdict (safe/flagged) and `logger.warning` when a message is flagged with kind and categories.

---

## 7. Automatic summary generation restored

**Issue:** Summary generation after source ingest was removed and left as a manual step. The initial plan listed it as a Week 1 deliverable.

**Fix:**
- `Backend/app/services/sourceService.py` — after `_set_status(source_id, "processed")`, `regenerate_summary(source_id)` is called automatically. Failure is caught, logged at `WARNING`, and does not affect the source's indexed status.

---

## 8. Test suite — all 93 tests now pass

**Issue:** The test suite had pre-existing failures that masked real regressions.

**Fix:**
- `Backend/tests/services/test_journalService.py` — rewritten. Removed 10 tests that referenced a removed API (`update_source_text`, inline chunking in `save_processed_source_file`, old `process_source` behaviour). Added 14 tests that match the current API. Fixed `test_transcribe_source_happy_path` to patch `update_source_transcript` (the real function name) and provide a `sentences` attribute on the mock transcript.
- `Backend/tests/services/test_thin_turn.py` — new file. 21 tests covering thin and non-thin inputs for `is_thin_turn`.
- `Backend/tests/services/test_rag_retrieval.py` — fixed two pre-existing failures: mock lambda functions were missing `tags=None` parameter added to `retrieve_nodes` and `ranked_retrieve`.

---

## 9. Log noise — multipart and fsevents silenced

**Issue:** After enabling configurable logging, `multipart.multipart` (the Python multipart library used by FastAPI for file uploads) and `fsevents` (the macOS kernel event backend for watchdog) both logged at DEBUG by default. This produced hundreds of lines per file upload in the console, making it impossible to read the application's own log output.

**Fix:**
- `Backend/app/logging_config.py` — added `"multipart"` and `"fsevents"` to the list of silenced third-party libraries. Both are now capped at `WARNING` regardless of `LOG_LEVEL`.

---

## What was not changed

The following items from `ANALYSIS.md` were reviewed but not implemented in this session. They require more substantial design or architectural work:

| Item | Reason not implemented |
|---|---|
| Backend session state persistence (versioned files) | Large architectural change touching backend + frontend; requires its own sprint |
| Frontend `beginReflection()` session isolation | Depends on the backend session state endpoint above |
| Modular RAG pipeline (`retrieval.py`, `generation.py`, etc.) | Refactor; does not change behaviour, requires careful interface design first |
| BM25 hybrid retrieval | Depends on modular RAG pipeline above |
| Clarification gate | Depends on modular RAG pipeline above |
| API key authentication | Requires frontend change to send the key; not safe to add without coordinating |
| PII module design spec | Documentation task; not a code change |
| Model choice documentation | Documentation task; not a code change |
| SQLite encryption | Requires SQLCipher or equivalent; significant dependency change |
