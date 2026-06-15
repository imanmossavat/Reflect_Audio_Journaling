# PII Module — Integration Contract

**Status:** design contract (no implementation in this doc)
**Owners:** Engine = Pedro (piiBERT). Integration = Reflect backend team.
**Goal:** a contract precise enough to implement both sides independently without further clarification.

---

## 1. Purpose & scope

The PII module does **three** things in Reflect:

1. **Detect** PII spans in a note's text (powered by piiBERT).
2. **Recognise & map entities** — cluster detections into canonical entities and track
   their occurrences *across* notes, so the UI can show recurring people/places/orgs.
   This is stored as **metadata**.
3. **Redact on export** — when the user exports one or more notes, replace PII using a
   chosen strategy (synthetic substitution / obfuscation / mask / removal),
   **consistently** across the whole export.

### Hard rules (non-negotiable invariants)

- **Notes are stored raw.** The module **never** mutates a source's stored `text` /
  `text_html`. Detection produces metadata only.
- **Redaction is pure and on-demand.** It takes text + spans and returns a *new* string.
  It is only invoked by the export flow, never at ingestion.
- **Detection is best-effort metadata.** If detection fails, the note still ingests,
  chunks, and indexes normally (RAG must not depend on PII).
- **Char offsets everywhere.** Every span uses character offsets into the exact string
  passed to the detector, with `text[start:end] == span.text`. (piiBERT's reference
  script emits *word* indices — converting to char offsets is part of the engine's job,
  see §4.1.)

---

## 2. Where it sits in the pipeline

Ingestion is the existing async background job
`Backend/app/services/sourceService.py::_process_source_sync`
(`transcribe → chunk → index`, each DB write short-lived). PII analysis is inserted as a
**new non-blocking step after text is available and before chunking**:

```
upload ──> source saved RAW (status: queued)
              │
              ▼  (background thread, _process_source_sync)
        ┌───────────────┐
        │ transcribe    │ (audio only)
        └──────┬────────┘
               ▼
        ┌────────────────────────────┐
        │ PII analyze  (NEW)         │  status: "analyzing"
        │  1. detect spans (piiBERT) │  ── best-effort: on error log + continue
        │  2. persist findings       │
        │  3. resolve → entity map   │
        └──────┬─────────────────────┘
               ▼
        ┌─────────────┐
        │ chunk       │  (unchanged, uses RAW text)
        └──────┬──────┘
               ▼
        ┌────────────────┐
        │ index (Chroma) │  (unchanged)
        └────────────────┘

Browsing:   UI ── GET /sources/{id}/entities, GET /entities  ──> entity metadata
Export:     UI ── POST /export {source_ids, strategy} ──> redacted bundle (on demand)
```

Redaction is **not** in the ingestion path. It lives entirely behind the export endpoint.

---

## 3. The trust boundary (who builds what)

| Layer | Owner | Delivered as |
|---|---|---|
| **Engine**: piiBERT wrapper implementing the `PiiDetector` protocol (§4) | Pedro | importable module `app.services.pii.detector` exposing `PiiBertDetector` |
| Detection service, entity resolution, redaction strategies, persistence, API | Reflect team | new files under `Backend/app/services/pii/`, `routes/`, `repositories/`, `schemas/` |

The engine is the **only** thing Pedro must deliver to spec. Everything else consumes the
`PiiDetector` protocol, so the engine can be swapped (or mocked in tests) freely.

---

## 4. Engine contract (Pedro owns)

### 4.0 Label set (fixed)

Derived from the model's `config.json` (`id2label`, with `B-`/`I-` prefixes stripped):

```python
PiiLabel = Literal[
    "ADDRESS", "CREDIT_CARD", "EMAIL", "ID", "LOCATION",
    "ORG", "PERSON", "PHONE", "SSN", "URL", "USERNAME",
]
```

These are the canonical labels used by the **whole** module. No remapping to spaCy
classes. If the label set changes, it changes here first.

### 4.1 Output type

```python
@dataclass(frozen=True)
class PiiSpan:
    start: int          # char offset into the text passed to detect() (inclusive)
    end: int            # char offset (exclusive); text[start:end] == self.text
    label: PiiLabel
    text: str           # exact surface substring
    confidence: float   # 0.0–1.0 (mean token confidence for the entity)
    detector: str = "piibert"   # provenance tag
```

**Word-index → char-offset rule.** `bertInference.py` returns
`start_word_index`/`end_word_index` over a whitespace split. The engine MUST convert these
to character offsets against the original string (e.g. tokenize with
`return_offsets_mapping=True`, or track cumulative offsets while splitting). The adapter is
responsible for this; downstream code only ever sees char offsets.

### 4.2 Protocol

```python
from typing import Protocol

class PiiDetector(Protocol):
    def detect(self, text: str) -> list[PiiSpan]: ...
    def detect_batch(self, texts: list[str]) -> list[list[PiiSpan]]: ...
```

### 4.3 Behavioural requirements

- **Offset fidelity:** for every span, `text[span.start:span.end] == span.text`.
- **Long input:** must handle text longer than the model's 512-token window via internal
  striding (the reference script already does `stride=64`); offsets remain global to the
  full input string.
- **Thresholding:** spans below the confidence threshold are dropped. Threshold is set at
  construction: `PiiBertDetector(model_path: str, threshold: float = 0.5)`.
- **Determinism:** same input → same output. No network calls. Eval mode, `no_grad`.
- **Empty / no-PII input:** returns `[]` (never raises).
- **Ordering:** spans returned sorted by `start` ascending; no two returned spans overlap
  (resolve overlaps inside the engine, keep highest confidence).
- **Concurrency:** `detect` is called inside `asyncio.to_thread`. The model is loaded
  **once** and reused; instances must be safe to call from a worker thread. Loading is
  lazy/singleton (don't load at import time).
- **Model location:** path comes from settings key `pii_model_path`
  (default: `models/piiBERTmodelV4/checkpoint-8912`). The engine does not hard-code paths.

### 4.4 Engine constructor

```python
class PiiBertDetector:                      # implements PiiDetector
    def __init__(self, model_path: str, threshold: float = 0.5,
                 device: str | None = None): ...
```

`device=None` → auto (`cuda` if available else `cpu`).

---

## 5. Integration data model (Reflect team owns)

### 5.1 In-memory types

```python
@dataclass
class PiiEntity:
    id: str
    label: PiiLabel
    canonical: str         # display form, e.g. "John Doe"
    aliases: list[str]     # distinct surface forms seen (normalised)
    occurrence_count: int

@dataclass
class PiiOccurrence:
    entity_id: str
    source_id: int
    span: PiiSpan
```

### 5.2 Persistence

Raw note text already lives on `source`. We persist two things as metadata:

- **findings** — one row per detected span (`source_id`, `start_char`, `end_char`,
  `label`, `surface`, `confidence`).
- **entities** — the canonical entities plus their occurrences (which finding in which
  source). Aliases can start as a JSON column on the entity rather than a separate table.

Exact table layout is left to the implementer; the only requirements are that findings link
to a source and entities link to their occurrences, and that **deleting a source removes
its findings and occurrences**.

---

## 6. Service interfaces (Reflect team owns)

Module: `Backend/app/services/pii/service.py`. All functions take an explicit `Session`
(matching the repo convention) or run inside the background job's short-lived sessions.

### 6.1 Detection

```python
def extract_pii(text: str) -> list[PiiSpan]:
    """Thin wrapper over the singleton PiiDetector. Pure; no DB. Returns [] on empty."""
```

### 6.2 Ingestion-time analysis (called from the background job)

```python
def analyze_source(session: Session, source_id: int) -> list[PiiEntity]:
    """Detect PII in the source's RAW text, persist findings, and update the global
    entity map. Idempotent: re-running deletes prior findings/occurrences for this
    source first (mirrors the chunk-retry pattern in _process_source_sync).
    Best-effort: callers treat exceptions as non-fatal."""
```

Wired into `_process_source_sync` after transcript text exists and **before** `chunk_text`:

```python
_set_status(source_id, "analyzing")
try:
    with Session(engine) as s:
        analyze_source(s, source_id)
except Exception as exc:
    logger.warning(f"PII analysis failed for source {source_id}: {exc}")  # continue
```

### 6.3 Entity resolution

```python
def resolve_entities(session: Session, findings: list[PiiFindingRow]) -> list[PiiEntity]:
    """Cluster findings into canonical entities and link occurrences, merging into the
    existing cross-note entity map."""
```

**Matching rules (keep it simple for v1):**

- Only spans with the **same label** can merge (PERSON "Apple" never merges with ORG "Apple").
- Normalise the surface form (trim, collapse whitespace, casefold) and merge on **exact
  normalised match**. Unseen surface forms are added as aliases of the matched entity.

That's enough to surface recurring entities. Fuzzy/nickname matching (e.g. "John" ↔
"John Doe") is a deliberate later improvement, not part of this contract.

### 6.4 Browsing (read APIs back these)

```python
def get_entities_for_source(session: Session, source_id: int) -> list[PiiEntity]: ...
def list_entities(session: Session, *, label: PiiLabel | None = None,
                  min_occurrences: int = 1) -> list[PiiEntity]: ...
def get_entity(session: Session, entity_id: str) -> tuple[PiiEntity, list[PiiOccurrence]]: ...
```

### 6.5 Redaction (export only)

```python
class RedactionStrategy(str, Enum):
    MASK      = "mask"       # "[PERSON]"
    TOKEN     = "token"      # "[PERSON_1]" — stable per entity within an export
    SYNTHETIC = "synthetic"  # realistic fake (LLM/Faker), stable per entity
    REMOVE    = "remove"     # delete the span entirely

@dataclass
class Replacement:
    span: PiiSpan
    replacement: str
    entity_id: str | None    # set when consistency was applied via the entity map

@dataclass
class RedactionResult:
    text: str
    replacements: list[Replacement]

def redact_text(
    text: str,
    spans: list[PiiSpan],
    strategy: RedactionStrategy,
    *,
    entity_resolver: "ExportEntityMap | None" = None,
) -> RedactionResult: ...
```

**Redaction requirements:**

- Apply replacements **right-to-left** (descending `start`) so offsets stay valid.
- **Consistency:** for `TOKEN` and `SYNTHETIC`, the same entity maps to the **same**
  replacement everywhere — within a note *and* across all notes in a multi-note export.
  This is what `ExportEntityMap` carries (built once per export, shared across sources).
- Overlapping spans: keep the higher-confidence one (engine already de-overlaps, but the
  redactor must not assume it).
- `SYNTHETIC` substitution is label-aware (PERSON→fake name, EMAIL→fake email, …). The
  generator is injectable so tests can stub the LLM/Faker and stay deterministic.
- Pure function: never touches the DB, never mutates inputs.

### 6.6 Export orchestration

```python
@dataclass
class ExportItem:
    source_id: int
    title: str | None
    redacted_text: str

@dataclass
class ExportBundle:
    items: list[ExportItem]
    strategy: RedactionStrategy
    entity_legend: dict[str, str]   # replacement -> label (optional, for the user)

def export_sources(
    session: Session,
    source_ids: list[int],
    strategy: RedactionStrategy,
    *,
    redetect: bool = True,
) -> ExportBundle:
    """Load RAW text for each source, obtain spans (re-detect, or reuse stored findings
    when redetect=False), build ONE shared ExportEntityMap, redact each note against it,
    and return the bundle. Stored notes are never modified."""
```

---

## 7. API surface (FastAPI routes)

New router `Backend/app/routes/pii.py`, mounted under the existing app in `main.py`.
Response bodies are Pydantic schemas in `Backend/app/schemas/piiSchemas.py`.

| Method & path | Body / query | Returns | Notes |
|---|---|---|---|
| `GET /sources/{id}/entities` | — | `list[EntityOut]` | entities detected in one note |
| `GET /entities` | `?label=&min_occurrences=` | `list[EntityOut]` | global map; recurring entities |
| `GET /entities/{entity_id}` | — | `EntityDetailOut` | entity + occurrences (which notes) |
| `POST /export` | `ExportRequest` | `ExportResponse` | on-demand redacted bundle |

```python
class EntityOut(BaseModel):
    id: str
    label: PiiLabel
    canonical: str
    aliases: list[str]
    occurrence_count: int

class OccurrenceOut(BaseModel):
    source_id: int
    start_char: int
    end_char: int
    confidence: float

class EntityDetailOut(EntityOut):
    occurrences: list[OccurrenceOut]

class ExportRequest(BaseModel):
    source_ids: list[int]
    strategy: RedactionStrategy = RedactionStrategy.SYNTHETIC

class ExportResponse(BaseModel):
    strategy: RedactionStrategy
    items: list[ExportItem]          # source_id, title, redacted_text
    entity_legend: dict[str, str]
```

Errors: unknown `source_id` → 404; empty `source_ids` → 400; detector unavailable on
export → 503 (export needs PII to be meaningful, unlike ingestion which degrades).

---

## 8. Data flow summary

**Ingestion (metadata only):**
```
raw text ─> extract_pii() ─> [PiiSpan] ─> persist pii_finding
                                       └─> resolve_entities() ─> pii_entity (+alias, +occurrence)
raw text is untouched and flows on to chunk_text() unchanged.
```

**Browse:**
```
GET /entities ─> list_entities() ─> entity map (recurring across notes)
```

**Export (on demand):**
```
POST /export {ids, strategy}
   ─> load RAW text per source
   ─> spans (re-detect OR stored findings)
   ─> build ONE ExportEntityMap (cross-note consistency)
   ─> redact_text() per source  (right-to-left, label-aware)
   ─> ExportBundle (raw notes still intact in DB)
```

---

## 9. Configuration

New settings (via existing `get_setting`):

| key | default | meaning |
|---|---|---|
| `pii_model_path` | `models/piiBERTmodelV4/checkpoint-8912` | piiBERT checkpoint dir |
| `pii_confidence_threshold` | `0.5` | drop spans below this |

---

## 10. Testing strategy

### 10.1 Shared golden fixture (the contract's source of truth)

`Research/PII/fixtures/golden.jsonl` — each line: `{ "text": ..., "spans": [{start,end,label,text}, ...] }`.
Both Pedro's engine tests and the integration tests assert against this file, so "correct
detection" means the same thing on both sides. Confidence is excluded from golden equality
(asserted only as `> threshold`).

### 10.2 Engine unit tests (Pedro)

- **Offset fidelity:** `text[s.start:s.end] == s.text` for every span, including text with
  unicode, punctuation, and multiple spaces (guards the word→char conversion).
- **Label validity:** every label ∈ `PiiLabel`.
- **Threshold:** spans below threshold are dropped; lowering threshold yields ≥ as many.
- **Long input:** PII near the end of a >512-token document is still found with correct
  global offsets (striding).
- **Empty / no-PII:** returns `[]`, no exception.
- **No overlaps / sorted:** output invariants from §4.3 hold.
- **Golden:** detections match `golden.jsonl` (allow span-boundary tolerance of 0 chars;
  flag near-misses).

### 10.3 Integration unit tests (Reflect team) — detector mocked

Use a `FakePiiDetector` returning scripted spans (no model load → fast, deterministic).

- **redact_text:** right-to-left safety (multiple spans don't corrupt offsets); each
  strategy output shape; overlapping spans resolved; idempotent for `MASK`.
- **consistency:** same entity → identical `TOKEN`/`SYNTHETIC` replacement within and
  across notes.
- **resolve_entities:** exact normalised clustering; cross-source merge; alias
  accumulation; label separation (PERSON vs ORG never merge).
- **analyze_source:** persists expected findings/entities; re-running is idempotent
  (no duplicate findings/occurrences).

### 10.4 Integration tests (with DB, detector still mockable)

- **Pipeline resilience:** detector that raises → source still reaches `processed`
  (chunks + Chroma index created); PII step logged as failed but non-fatal.
- **Cascade delete:** deleting a source removes its findings + occurrences; orphaned
  entity pruned.
- **Export multi-note consistency:** two notes mentioning the same person export with the
  **same** synthetic name; raw `source.text` unchanged after export.
- **API contract:** `GET /entities`, `GET /sources/{id}/entities`,
  `GET /entities/{id}`, `POST /export` return the schemas in §7; 404/400/503 paths.

### 10.5 Optional model smoke test

One `@pytest.mark.slow` test that loads the real checkpoint and asserts a couple of obvious
detections (e.g. an email + a person), kept out of the default CI run.

---

## 11. Out of scope (explicit, for this contract)

- Reversible at-rest tokenization / vault (we store raw; not needed while everything is
  on-device). Revisit only if cloud sync is added.
- Display/query-time masking in the main app UI (raw is shown to the owner by design).
- PII detection on audio directly (we operate on the transcript text).
- Non-English models (label set + thresholds are tuned for the shipped checkpoint).

---

## 12. Definition of done

- [ ] `PiiBertDetector` implements §4, passes §10.2 + the golden fixture.
- [ ] `pii_finding` / `pii_entity` / alias / occurrence tables + repository created.
- [ ] `analyze_source` wired into `_process_source_sync` (non-blocking, idempotent).
- [ ] `resolve_entities`, `redact_text` (4 strategies), `export_sources` implemented + §10.3 green.
- [ ] Routes in §7 mounted + §10.4 green.
- [ ] Settings keys in §9 registered with defaults.
