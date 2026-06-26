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
| **event skeleton** | Structurally pre-filled event (entities, arc, timestamp) that the LLM only writes text for |
| **knowledge graph** | Directed graph of entities, arcs, and latent facts used for validation and trajectory sampling |
| **note corpus** | Human-like memory fragments generated from the event stream — the retrieval corpus |
| **QA set** | Questions and answers grounded only in the note corpus, with gold supporting note IDs |
| **validator** | Code-side structural checks that enforce schema, references, and ordering |

These layers must not bleed into each other. Later stages only see what they are supposed to see.

---

## Pipeline

```
config.py / prompts.py / llm.py   →  shared modules (model, paths, prompts, retries)
             ↓
Stage 01: World State       →  data/world_state.json
             ↓ knowledge_graph.py
Stage 02: Event Timeline    →  data/events_raw.json
             ↓ graph-based validator + repair
Stage 03: Repair Pass       →  data/events_repaired.json
Stage 04: Note Generation   →  data/notes.json
Stage 05: QA Generation     →  data/qa_pairs.json
```

### Key architectural decisions

**Centralised configuration and prompts.**
`config.py` is the single source of truth for the model, backend, pipeline duration, and file paths — no stage file hardcodes these. `prompts.py` holds every LLM prompt as a plain string constant, separating prompt tuning from pipeline logic. `llm.py` exposes one shared `call_llm()` function with built-in retry logic, used by every stage instead of duplicating an Ollama/Anthropic client five times.

**Knowledge graph as structural backbone.**
`knowledge_graph.py` converts the world state into a queryable `networkx` directed graph. It serves two roles: (1) a deterministic validator that replaces LLM-based repair, and (2) a biased random walk sampler that pre-fills event skeletons before the LLM writes any text.

**Event skeletons.**
Stage 02 does not ask the LLM to invent the full structure of each event. Instead, `knowledge_graph.py` generates skeletons with `story_arc_id`, `involved_entities`, and `timestamp` already set. The LLM only writes `text` and `latent_fact_updates`. This eliminates the most common source of structural errors (unknown entity IDs, invalid arc references).

**Biased random walk for event selection.**
Entities are scored per iteration: connected to an unresolved arc (+3.0), dormant for longer (+0–2.0 recency decay), more connected in the graph (+0.1 per edge). This produces organic, uneven event distribution without asking the LLM to manage it.

**Contradiction injection.**
Stage 02 explicitly injects contradiction skeletons: for each unresolved arc, a second event is added later in the timeline that must revise or contradict a fact from the first. This ensures `conflict_resolution` QA pairs are possible.

**Graph-based repair (Stage 03).**
Structural errors are caught deterministically: unknown entities are stripped, invalid arc IDs are nulled, importance is clamped to 1–5, and timestamps are re-sorted. No LLM needed. The minimal-edit principle applies: messiness in event text is preserved.

**Evidence-first QA generation (Stage 05).**
Supporting notes are chosen before the question is written, not after. Five QA types are generated with dedicated seed finders: `single_hop`, `multi_hop`, `temporal_reasoning`, `conflict_resolution`, and `unanswerable`. Gold evidence is locked at generation time.

---

## Design principles

**One primary user only.** The dataset should feel like a single real person's messy continuity, not a constructed fictional profile.

**Recurring entities across domains.** Entities recur in multiple contexts so retrieval must disambiguate by time and situation.

**Evolution over static memory.** Facts change, contradict, decay, and reappear over time.

**Notes must not add hidden facts.** The note layer only surfaces what the event stream already contains. The MESSINESS_RULES in the Stage 04 prompt enforce this by preventing the LLM from stating latent facts directly.

**Questions answered from notes only.** Evaluation relies on the note corpus and metadata, not the hidden world state.

**Literal support over interpretation.** QA answers stay source-grounded and avoid unsupported psychological or causal claims.

**Competing explanations are allowed.** Some events support more than one plausible interpretation, but only one is fully supported when evidence is complete.

---

## QA difficulty levels

The five QA types form a difficulty ladder:

| Type | What the RAG system must do | Min. notes needed |
|------|-----------------------------|-------------------|
| `single_hop` | Retrieve one relevant note and read it | 1 |
| `multi_hop` | Combine facts across multiple notes about the same entity | 2+ |
| `temporal_reasoning` | Reconstruct the order of events across notes | 3 |
| `conflict_resolution` | Identify which of two contradicting notes is more recent | 2 |
| `unanswerable` | Recognise that the answer is not in the corpus and abstain | — |

---

## Known caveats

| Caveat | Why it matters |
|--------|---------------|
| Latent fact leakage | If event text reads like a psychology summary, QA becomes easier than intended. The MESSINESS_RULES in Stage 04 mitigate this. |
| Story arc drift | Arc meaning can shift across a long timeline unless definitions are fixed at generation |
| Direct event-to-QA coupling | Questions generated too close to events make retrieval unrealistically easy |
| Unsupported inferences | Answers must stay literal; emotional or causal claims not in the notes weaken evaluation fidelity |
| Schema drift | Small extra keys or naming inconsistencies cause downstream parsing failures — the validator catches these |
| Skeleton override | The LLM may still overwrite structural skeleton fields if not explicitly forbidden in the prompt |