# Synthetic RAG Memory Dataset Pipeline

Lean 4-stage pipeline for generating synthetic RAG evaluation benchmarks.

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

## Setup

```bash
pip install anthropic jsonschema
export ANTHROPIC_API_KEY=sk-...
```

## Usage

```bash
# Run full pipeline
python pipeline.py

# Run only one stage (loads prior outputs from disk)
python pipeline.py --stage 2

# Resume from a stage (runs that stage and all after)
python pipeline.py --from-stage 3

# Validate existing outputs without generating anything
python pipeline.py --validate-only
```

## Output files

| File | Contents |
|------|----------|
| `outputs/world_state.json` | Hidden canonical truth: entities, arcs, projects, latent facts |
| `outputs/event_stream.json` | 90-day chronological event stream |
| `outputs/note_corpus.json` | Human-like notes derived from events (the retrieval corpus) |
| `outputs/qa_set.json` | QA pairs with gold supporting note IDs |

## What the validator checks

**World state**
- JSON schema conformance
- ≥10 entities, ≥3 story arcs

**Event stream**
- Unique event IDs
- Strictly monotonic ISO timestamps
- All `story_arc_id` references exist in world state
- All `involved_entities` exist in world state

**Note corpus**
- Unique note IDs
- All `story_arc_id` references exist in world state
- No suspiciously empty note text

**QA set**
- All `supporting_notes` reference real note IDs
- Answerable questions have at least one supporting note
- Unanswerable questions have no supporting notes
- At least some unanswerable questions present

## Design decisions

**No LLM repair pass (original Stage 3)**
Structural errors (bad arc IDs, duplicate events, timestamp ordering) are
caught deterministically by the validator. An LLM repair pass costs tokens,
is slow, and risks silent content rewrites that contaminate the benchmark.

**No LLM QA audit (original Stage 6)**
The Stage 4 / Stage 5 prompts already carry the literal-and-source-grounded
constraint. If QA quality is poor, the fix belongs in the prompt, not a
downstream audit pass. The validator catches structural issues; human spot
review handles edge cases.

**Shared constraint block**
All four stage prompts share a single injected constraint block (no new facts,
stay literal, return only JSON). Duplication in the original spec has been
eliminated.

## Files

```
rag_pipeline/
├── pipeline.py        # Main runner
├── prompts.py         # All four stage prompts
├── validator.py       # Code-side validation (no LLM)
├── schemas/
│   ├── world_state.json
│   ├── event_stream.json
│   ├── note_corpus.json
│   └── qa_set.json
└── outputs/           # Generated at runtime
```
