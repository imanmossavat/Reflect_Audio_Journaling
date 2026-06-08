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

The original Stage 3 (LLM repair pass) and Stage 6 (LLM QA audit) are
replaced by `validator.py`, which enforces all structural constraints in
code — faster, cheaper, and without risk of silent content rewrites.

---

## Setup

### Option A — Anthropic API (recommended for quality)

Requires a paid API account at console.anthropic.com. Not the same as a
Claude.ai subscription.

```bash
pip install anthropic jsonschema
export ANTHROPIC_API_KEY=sk-...
```

### Option B — Ollama (local, free)

Requires Ollama installed and running locally. No API key needed.

```bash
pip install openai jsonschema   # openai SDK talks to Ollama's compatible endpoint
ollama serve                    # start Ollama (if not already running)
ollama pull qwen2.5:32b         # download your chosen model
```

#### Recommended Ollama models

| Model | RAM needed | JSON reliability | Notes |
|-------|-----------|-----------------|-------|
| `qwen2.5:72b` | ~45 GB | Best | Top choice if you have the VRAM |
| `qwen2.5:32b` | ~22 GB | Very good | Best balance of quality and size |
| `llama3.1:70b` | ~40 GB | Good | Strong alternative |
| `phi4` | ~6 GB | Decent | Use for prototyping only |
| `llama3.1:8b` | ~5 GB | Unreliable | Struggles with complex JSON schemas |

Use at least a 32B model for production runs. Smaller models will frequently
break the JSON schema, requiring manual fixes between stages.

---

## Usage

```bash
# Anthropic backend (default)
python pipeline.py

# Ollama backend, default model (qwen2.5:32b)
python pipeline.py --backend ollama

# Ollama backend, specific model
python pipeline.py --backend ollama --model qwen2.5:72b

# Override Anthropic model
python pipeline.py --model claude-haiku-4-5-20251001   # cheaper, faster

# Run only one stage (loads prior outputs from disk)
python pipeline.py --stage 2

# Resume from a stage (runs that stage and all after)
python pipeline.py --from-stage 3 --backend ollama

# Validate existing outputs without generating anything
python pipeline.py --validate-only
```

---

## Output files

| File | Contents |
|------|----------|
| `outputs/world_state.json` | Hidden canonical truth: entities, arcs, projects, latent facts |
| `outputs/event_stream.json` | 90-day chronological event stream |
| `outputs/note_corpus.json` | Human-like notes derived from events (the retrieval corpus) |
| `outputs/qa_set.json` | QA pairs with gold supporting note IDs |

---

## What the validator checks

**World state** — schema conformance, ≥10 entities, ≥3 story arcs

**Event stream** — unique event IDs, strictly monotonic ISO timestamps,
all `story_arc_id` and `involved_entities` references exist in world state

**Note corpus** — unique note IDs, all `story_arc_id` references valid,
no suspiciously empty note text

**QA set** — all `supporting_notes` reference real note IDs, answerable
questions have supporting notes, unanswerable questions do not, at least
some unanswerable questions present

---

## Design decisions

**No LLM repair pass (original Stage 3)**
Structural errors are caught deterministically by the validator. An LLM
repair pass costs tokens, is slow, and risks silent content rewrites that
contaminate the benchmark.

**No LLM QA audit (original Stage 6)**
If QA quality is poor, the fix belongs in the Stage 4 prompt. The validator
catches structural issues; human spot review handles edge cases.

**Shared constraint block**
All four stage prompts share a single injected constraint block (no new facts,
stay literal, return only JSON). Duplication from the original spec eliminated.

**Ollama via OpenAI-compatible endpoint**
Ollama exposes an OpenAI-compatible API at `localhost:11434/v1`, so the same
`openai` Python SDK works for both OpenAI and Ollama. No separate Ollama SDK
needed. Retry count is set to 3 (vs 2 for Anthropic) to account for local
models being less reliable at JSON output.

---

## Files

```
rag_pipeline/
├── pipeline.py        # Main runner — only file that differs per backend
├── prompts.py         # All four stage prompts (backend-agnostic)
├── validator.py       # Code-side validation (no LLM, no backend dependency)
├── schemas/
│   ├── world_state.json
│   ├── event_stream.json
│   ├── note_corpus.json
│   └── qa_set.json
└── outputs/           # Generated at runtime
```
