# Synthetic RAG Memory Dataset Pipeline

A controlled benchmark pipeline for evaluating retrieval-augmented generation (RAG) systems using synthetic, memory-like data grounded in a single user's life.

---

## What it tests

Whether a RAG system can:

- track state changes over time
- compose multi-hop evidence from scattered notes
- reason across long, noisy context
- maintain long-horizon memory across sessions
- resolve contradictions and competing explanations
- abstain when evidence is missing

This is intentionally not a standard RAG corpus. Hidden truth, visible text, and evaluation labels are kept in separate layers so each stage can be tested independently.

---

## Benchmark anchors

The design draws from these benchmark families:

| Benchmark | What it contributes |
|-----------|-------------------|
| bAbI | State tracking, temporal updates, structured reasoning |
| HotpotQA | Multi-hop evidence across scattered support |
| MuSiQue | Compositional reasoning with non-local evidence |
| NarrativeQA | Long-form narrative understanding |
| QuALITY | Long-context reading with distractors and underdetermined answers |
| LoCoMo | Long-horizon conversational memory and session-level drift |
| LongMemEval | Memory updates, temporal reasoning, and abstention |

These are design anchors only. The dataset is synthetic, internally consistent, and grounded in its own generated evidence.

---

## Core terminology

| Term | Definition |
|------|-----------|
| **latent world state** | Hidden canonical structure — ground truth the model never sees directly |
| **event stream** | Chronological sequence of state-changing events derived from the world state |
| **note corpus** | Human-like memory fragments generated from the event stream — the retrieval corpus |
| **QA set** | Questions and answers grounded only in the note corpus, with gold supporting note IDs |
| **validator** | Code-side structural checks that enforce schema, references, and ordering |

These layers must not bleed into each other. Later stages only see what they are supposed to see.

---

## Pipeline

```
Stage 1: World State     →  hidden entities, arcs, projects, latent facts
Stage 2: Event Stream    →  N-day chronological events
         ↓ code validator    (schema, timestamps, entity/arc cross-refs)
Stage 3: Note Corpus     →  human-like notes from events (the retrieval corpus)
Stage 4: QA Set          →  questions, answers, gold supporting note IDs
```

The original 6-stage spec included an LLM repair pass (Stage 3) and an LLM QA audit (Stage 6). Both were removed:

- **Repair pass replaced by `validator.py`** — structural errors (bad arc IDs, duplicate events, timestamp ordering) are caught deterministically in code. An LLM repair pass costs tokens, is slow, and risks silent content rewrites that contaminate the benchmark.
- **QA audit dropped** — if QA quality is poor, the fix belongs in the Stage 4 prompt. The validator catches structural issues; human spot review handles edge cases.

---

## Design principles

**One primary user only.** The dataset should feel like a single real person's messy continuity, not a constructed fictional profile.

**Recurring entities across domains.** Entities recur in multiple contexts so retrieval must disambiguate by time and situation.

**Evolution over static memory.** Facts change, contradict, decay, and reappear over time.

**Notes must not add hidden facts.** The note layer only surfaces what the event stream already contains.

**Questions answered from notes only.** Evaluation relies on the note corpus and metadata, not the hidden world state.

**Literal support over interpretation.** QA answers stay source-grounded and avoid unsupported psychological or causal claims.

**Competing explanations are allowed.** Some events support more than one plausible interpretation, but only one is fully supported when evidence is complete.

---

## Known caveats

| Caveat | Why it matters |
|--------|---------------|
| Latent fact leakage | If event text reads like a psychology summary, QA becomes easier than intended |
| Story arc drift | Arc meaning can shift across a long timeline unless definitions are fixed at generation |
| Direct event-to-QA coupling | Questions generated too close to events make retrieval unrealistically easy |
| Unsupported inferences | Answers must stay literal; emotional or causal claims not in the notes weaken evaluation fidelity |
| Schema drift | Small extra keys or naming inconsistencies cause downstream parsing failures — the validator catches these |

---

## Configuration

All tunable parameters live in `config.py`:

```python
DURATION_DAYS   = 90          # 7 = one week, 14 = two weeks
MIN_ENTITIES    = 10
MAX_ENTITIES    = 20
BACKEND         = "anthropic" # or "ollama"
ANTHROPIC_MODEL = "claude-opus-4-6"
OLLAMA_MODEL    = "qwen2.5:32b"
```

See `README.md` for setup and usage instructions.
