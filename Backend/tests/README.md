# Backend Testing Architecture

This directory contains a comprehensive test suite for the REFLECT engine, ensuring reliability across services, processing pipelines, and API endpoints.

## 📂 Structure & Coverage

The tests are organized into three layers, mirroring the application architecture:

### 1. **Unit Tests (`tests/services/`)**
These tests focus on the isolated logic of individual services.
- `test_pii.py`: Validates regex and NER-based detection, deduplication, and reverse-redaction logic to prevent index drift.
- `test_prosody.py`: Tests signal analysis features like RMS energy, speaking rate (WPM), and silence detection using synthetic audio buffers.
- `test_recordings.py`: Validates metadata lifecycle, recording library serialization, and full-object retrieval.
- `test_segmentation.py`: Exercises topic-boundary detection (adaptive/spectral) and automated labeling using noun-phrase extraction.
- `test_semantic_search.py`: Verifies vector search logic, scoring thresholds, and result capping per recording.
- `test_storage.py`: Tests low-level file operations, atomic JSON writes, and the directory pruning mechanism.
- `test_transcription.py`: Validates the WhisperX wrapper, FFmpeg audio decoding, and word-alignment extraction.

### 2. **Pipeline Tests (`tests/pipelines/`)**
Integration tests for the orchestration layer.
- `test_processing.py`: Simulates end-to-end flows like `process_uploaded_audio` and `process_after_edit`, ensuring that services interact correctly (e.g., transcription output feeding into segmentation).

### 3. **API Integration Tests (`tests/api/`)**
Tests the REST interface using FastAPI's `TestClient`.
- `test_routes.py`: Covers the main application endpoints for recordings, settings, and AI tools.
- `test_setup_routes.py`: Covers initialization logic and system requirement checks.

---

## 🛠 Shared Fixtures (`conftest.py`)

We use several global fixtures to ensure tests are fast, clean, and isolated:

- **`test_setup`**: (Function-scoped, Autouse)
  - Automatically creates a temporary `DATA_DIR` and `CONFIG_DIR` using `tempfile`.
  - Overrides `app.core.config.settings` for the duration of the test.
  - Ensures no real user data is modified and every test starts with a "blank slate."
- **`client`**: 
  - Provides a pre-configured `FastAPI.testclient.TestClient` for making requests to the API.

---

## 🧪 Developer Guidelines

### Running Tests
Run the full suite from the `Backend` directory:
```powershell
.\.venv\Scripts\python -m pytest tests -vv
```

### Adding New Tests
1. **Mock Heavy Dependencies**: Always mock AI models (WhisperX, spacy, SentenceTransformer) in `__init__` or using fixtures. We should not download models during CI or local testing.
2. **Patching Paths**: Remember to patch the class/module where the dependency is **imported**, not where it is defined.
   - *Example*: Use `patch("app.services.pii.spacy.load")` instead of `patch("spacy.load")`.
3. **Async Tests**: Use `@pytest.mark.asyncio` for any tests involving `async def` functions.

### Common Mocks
- **Audio**: Use `np.zeros(N)` or `np.random.rand(N)` to simulate audio signals.
- **FFmpeg**: Mock `subprocess.run` to return dummy binary buffers to avoid dependency on system binaries during most unit tests.
