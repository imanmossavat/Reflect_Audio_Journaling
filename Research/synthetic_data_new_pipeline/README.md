# Synthetic RAG Memory Dataset Pipeline

Lean 4-stage pipeline for generating synthetic RAG evaluation benchmarks.
Supports two backends: the **Anthropic API** (paid, highest quality) and
**Ollama** (local, free, no internet required).

## Architecture

```
Stage 1: World State     → outputs/world_state.json
Stage 2: Event Stream    → outputs/event_stream.json
         ↓ code validator (replaces LLM repair pass)
Stage 3: Note Corpus     → outputs/note_corpus.json
Stage 4: QA Set          → outputs/qa_set.json
```

---

## Configuration

**All tunable parameters live in `config.py`. That is the only file you need to edit for most changes.**

```python
# config.py

DURATION_DAYS   = 90          # 7 = one week, 14 = two weeks, 90 = three months

MIN_ENTITIES    = 10          # lower bound enforced by validator
MAX_ENTITIES    = 20          # instruction to the model

BACKEND         = "anthropic" # "anthropic" | "ollama"
ANTHROPIC_MODEL = "claude-opus-4-6"
OLLAMA_MODEL    = "qwen2.5:32b"
OLLAMA_BASE_URL = "http://localhost:11434/v1"

MAX_TOKENS      = 8192
MAX_RETRIES     = 3
```

CLI flags override `config.py` for one-off runs without editing the file:

```bash
python pipeline.py --days 14                        # two-week run
python pipeline.py --backend ollama --days 7        # one week, local model
python pipeline.py --model qwen2.5:72b              # different model
```

---

## Setup

### Option A — Anthropic API (recommended for quality)

Requires a paid API account at console.anthropic.com (not a Claude.ai subscription).

```bash
pip install anthropic jsonschema
export ANTHROPIC_API_KEY=sk-...
```

### Option B — Ollama (local, free)

```bash
pip install openai jsonschema
ollama serve                    # start Ollama if not already running
ollama pull qwen2.5:32b         # or whichever model you choose
```

#### Recommended Ollama models

| Model | RAM needed | JSON reliability | Notes |
|-------|-----------|-----------------|-------|
| `qwen2.5:72b` | ~45 GB | Best | Top choice if you have the VRAM |
| `qwen2.5:32b` | ~22 GB | Very good | Best balance of quality and size |
| `llama3.1:70b` | ~40 GB | Good | Strong alternative |
| `phi4` | ~6 GB | Decent | Prototyping only |
| `llama3.1:8b` | ~5 GB | Unreliable | Struggles with complex JSON schemas |

Use at least a 32B model for production runs.

---

## Usage

```bash
# Full pipeline — uses config.py defaults
python pipeline.py

# Override duration without editing config.py
python pipeline.py --days 7
python pipeline.py --days 14

# Ollama backend
python pipeline.py --backend ollama
python pipeline.py --backend ollama --model qwen2.5:72b --days 14

# Run only one stage (loads prior outputs from disk)
python pipeline.py --stage 2

# Resume from a stage
python pipeline.py --from-stage 3

# Validate existing outputs without generating anything
python pipeline.py --validate-only
```

---

## Output files

| File | Contents |
|------|----------|
| `outputs/world_state.json` | Hidden canonical truth: entities, arcs, projects, latent facts |
| `outputs/event_stream.json` | Chronological event stream |
| `outputs/note_corpus.json` | Human-like notes derived from events (the retrieval corpus) |
| `outputs/qa_set.json` | QA pairs with gold supporting note IDs |

---

## What the validator checks

**World state** — schema conformance, ≥ `MIN_ENTITIES` entities, ≥3 story arcs

**Event stream** — unique event IDs, strictly monotonic ISO timestamps,
all `story_arc_id` and `involved_entities` references exist in world state

**Note corpus** — unique note IDs, all `story_arc_id` references valid,
no suspiciously empty note text

**QA set** — all `supporting_notes` reference real note IDs, answerable
questions have supporting notes, unanswerable questions do not, at least
some unanswerable questions present

---

## Files

```
rag_pipeline/
├── config.py          # ← edit this for duration, model, backend, paths
├── pipeline.py        # Main runner (reads from config.py)
├── prompts.py         # Stage prompts (reads from config.py)
├── validator.py       # Code-side validation (no LLM, no config dependency)
├── schemas/
│   ├── world_state.json
│   ├── event_stream.json
│   ├── note_corpus.json
│   └── qa_set.json
└── outputs/           # Generated at runtime
```

## Design decisions

**`config.py` as single source of truth**
Duration, entity counts, model names, and paths are defined once and imported
by both `pipeline.py` and `prompts.py`. CLI flags override config for one-off
runs without touching the file.

**No LLM repair pass (original Stage 3)**
Structural errors are caught deterministically by `validator.py`. An LLM
repair pass costs tokens, is slow, and risks silent content rewrites.

**No LLM QA audit (original Stage 6)**
If QA quality is poor, the fix belongs in the Stage 4 prompt. The validator
catches structural issues; human spot review handles edge cases.
