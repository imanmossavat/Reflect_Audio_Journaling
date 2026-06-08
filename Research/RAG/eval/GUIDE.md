# REFLECT RAG — implementation & iteration guide

Everything changed for the RAG improvement work (Metadata → Eval → Reranker), where it lives,
and **why** it's built this way so you can judge and iterate.

> **Layout update (post-restructure).** This folder was renamed `maya_eval/` → `eval/` and split
> into `harness/` (code) + `datasets/<name>/` (data) + `runs/`. Paths below that say `maya_eval/…`
> or bare `python ingest.py` now map to:
> - `python ingest.py`        → `python harness/ingest.py --dataset baseline`
> - `python run_eval.py …`    → `python harness/run_eval.py --dataset baseline …`
> - `notes.json` / `questions*.json` / `notes_index.json` → `datasets/baseline/…`
> - `results/<ts>/`           → `runs/baseline/<ts>/`
> - eval Chroma is now **per-dataset** (`chroma/<dataset>/`, collection `<dataset>_chunks`).
> The harder state-evolution corpus lives in `datasets/stateful/` — see `README.md`.

---

## 0. The pipeline (mental model)

A query flows through this, in order. Every change sits on one of these lines.

```
question
  → configure_llamaindex()        embed + LLM models (Ollama)
  → Chroma vector search (pool_k)  oversampled candidate pool
  → [hard filters]                 modality + temporal (Chroma `where`)
  → reranker.rerank()              BGE cross-encoder → relevance ∈ [0,1]
  → score_candidates()             blend: relevance + recency_decay
  → top_k                          final nodes
  → TEXT_QA_TEMPLATE + Ollama      answer
```

Guiding principle: **relevance is learned (cross-encoder), not keyword-matched; time/modality are
filters, not score nudges.** The old code did the opposite — lexical whitelists scored relevance and
nothing filtered structurally. That's what we inverted.

---

## 1. Phase 1 — Metadata at ingest + structured filters

**Why:** `created_at`/`file_type` only lived in SQLite and were consulted *after* retrieval. To filter
*inside* Chroma you must stamp the fields onto the vectors at ingest. Chroma metadata must be scalar,
so time is stored as an **epoch int** (`created_at_ts`) — that's what makes a range `where` possible.

| What | Where | Why |
|---|---|---|
| Read `source.created_at`; build `created_at_ts` + `modality` onto each chunk dict | `Backend/app/services/sourceService.py` `_process_source_sync` | The ingest worker is the only place holding both the chunks and the source row. |
| `_chunk_metadata()` stamps keys onto `TextNode.metadata` | `Backend/app/services/rag.py` | One source of truth; omits keys when `None` because **Chroma rejects `None`**. |
| Same helper mirrored in `upsert_chunks` | `Backend/app/services/chroma.py` | The direct-upsert fallback must stay in parity or it silently drops the fields. |
| `modality` param → `query_sources`/`retrieve_nodes` → `ranked_retrieve` → `MetadataFilter(key="modality", EQ)` | `Backend/app/routes/query.py`, `Backend/app/services/rag.py` | Replaces the deleted "voice→audio" keyword guess with an **explicit** filter the UI/API sets. |

**Deliberate caveat — new-ingests-only.** Chunks already in Chroma have no `created_at_ts`/`modality`, so
a modality filter won't match them. We skipped a bulk reindex on purpose; add one later if you want the
filter to apply retroactively. The **time** cutoff still works on all data because it routes through SQLite
(`get_source_ids_in_range` → `source_id IN`), which we left untouched.

---

## 2. Phase 2 — The eval harness (your iteration loop)

Lives in `Research/RAG/eval/`. Each dataset (`datasets/<name>/` with `notes.json`, `questions.json`
+ `gold_supporting_notes`, `notes_index.json`) plus `harness/_bootstrap.py` (isolates eval embeddings
into `chroma/<name>/`) drive the measurement + reproducibility layer.

**The loop** (run from `Research/RAG/eval/`):
```bash
python harness/ingest.py    --dataset baseline                  # chunk + index into the ISOLATED Chroma
python harness/run_eval.py  --dataset baseline --top-k 5            # reranker OFF (embedding baseline)
python harness/run_eval.py  --dataset baseline --top-k 5 --reranker # reranker ON (BGE cross-encoder)
# open harness/compare_runs.ipynb
```

| What | Where | Why |
|---|---|---|
| `metrics.py` — P@K, R@K, MRR, context_recall, context_precision, idk-rate | `metrics.py` | **Deterministic** retrieval metrics (gold labels known) — no LLM-judge noise, so reranker deltas are trustworthy. Pure function over `raw.jsonl`; you can re-score old runs anytime. |
| Run-folders `results/<UTC-ts>_<githash>/` + `config.json` + `summary.csv` | `run_eval.py` `_make_run_dir` | The commit hash makes a score reproducible — check out that hash and you can reproduce it ("eval = git"). |
| `_apply_eval_isolation()` | `run_eval.py` | See "isolation" below — without it the comparison is invalid. |
| `compare_runs.ipynb` | `compare_runs.ipynb` | Loads every run's `summary.csv` into one DataFrame, bar-plots metrics across runs, shows the recall-vs-precision gate. |

**How to read the metrics (so you can judge):**
- **Recall@K** — fraction of gold notes that landed in top-K. *Low recall ⇒ a reranker can't help* (the
  note isn't even retrieved); fix chunking/embedding upstream.
- **Precision@K** — fraction of your K results that are gold. *Low precision ⇒ junk is crowding the top* —
  **this is what a reranker fixes.**
- **MRR** — how high the *first* correct note ranks (1.0 = always rank 1). The single best "is the top
  result good?" number.
- **context_recall vs context_precision = the gate.** High recall + low precision → reranker is the lever.
- **unanswerable_idk_rate** — for the 5 unanswerable questions, did it correctly say "I don't know"?
  Guards against the reranker making the model hallucinate confidently.

**Why deterministic metrics here, not RAGAS/LLM-judge:** retrieval is a ranking problem with known gold
labels — you don't need an LLM to check whether `N-7815` is in the list. Save LLM-judge metrics
(faithfulness/relevancy) for the later *prompt* phase.

### Eval isolation — the subtle part (`_apply_eval_isolation`)
`_bootstrap.py` isolates Chroma but **not** the SQL DB. The synthetic `source_id`s 1–22 collide with real
journal rows, so `get_sources_meta` returned real timestamps and polluted recency. `_apply_eval_isolation`:
1. Stubs `get_sources_meta → {}` so recency is neutral (0.5 for all) — the eval measures *relevance ordering*, not recency on fake metadata.
2. With `--reranker` off, swaps `reranker.rerank` for identity (relevance = embedding score) — so off-vs-on
   is a **single-variable** comparison under one code path. Production code is untouched.

---

## 3. Phase 3 — Cross-encoder reranker + ranking rewrite

**Why we deleted the old code:** `metadata_signal` was three stacked exact-match whitelists (`MOOD_VOCAB`,
`_MODALITY`, tag-overlap). They fire only on literal token matches — "on edge" never matches "anxious" —
and need endless hand-curation. A cross-encoder reads query + chunk *together* and scores real semantic
relevance, making all three obsolete.

| What | Where | Why |
|---|---|---|
| `reranker.py` — lazy `BAAI/bge-reranker-v2-m3`, scores used directly | `Backend/app/services/reranker.py` | Local, multilingual (NL/EN), Apache-2.0. `@lru_cache` loads weights once. **`CrossEncoder.predict` already sigmoid-activates single-label models → output is [0,1]; do NOT sigmoid again** (that bug flattened everything to 0.5). |
| `ranking.py` rewritten: `combined_score(relevance, temporal)`, `RankWeights{relevance, temporal}`, `SourceMeta{created_at}` | `Backend/app/services/ranking.py` | Two principled signals instead of a heuristic pile. `recency_decay` stays — it's math, not a whitelist. |
| `score_candidates` takes `(node, relevance)` pairs | `Backend/app/services/ranking.py` | The reranker, not the embedding score, drives ranking. |
| `ranked_retrieve` calls `reranker.rerank` then blends | `Backend/app/services/rag.py` | The oversampled Chroma pool is what the cross-encoder reorders. |
| `get_sources_meta` slimmed to `created_at` only | `Backend/app/repositories/sourceRepository.py` | Recency is the only thing SQLite metadata still feeds. |
| Tests | `Backend/tests/services/test_{ranking,reranker,rag_retrieval}.py` | The retrieval test **stubs the reranker** so unit tests never download the 2 GB model. 17 pass. |

## 3b. Results so far — the reranker verdict depends on the dataset

Single-variable comparison (recency neutralized, `--reranker` off vs on), top_k=5:

| Dataset | Metric | OFF (embedding) | ON (BGE) | Verdict |
|---|---|---|---|---|
| `questions.json` (1 gold note each) | P@5 / R@5 / MRR | 0.22 / 0.975 / 0.935 | 0.22 / 0.975 / 0.797 | reranker **loses** |
| `questions_multi.json` (2–4 gold notes) | P@5 / R@5 / MRR | 0.34 / 0.525 / 0.90 | **0.50 / 0.767 / 0.95** | reranker **wins** |

**Why opposite results?** With one gold note per question, precision@5 is capped at 0.2 and the embedding
already ranks that note at ~rank 1 (MRR 0.935) — no headroom, so the reranker can only match or hurt. With
multi-note answers, recall/precision have real room and the cross-encoder fills the top-5 with more gold
notes. **Lesson: a reranker can only prove itself on a dataset where retrieval ordering actually matters.**
Realistic journaling queries ("what patterns appear in how I handle X") are multi-note, so the reranker
stays on by default. Run the harder set with `--questions questions_multi.json`.

Valid run folders: `133402Z` (multi off) vs `133649Z` (multi on); `131228Z` (single off) vs `131711Z`
(single on). Delete the pre-fix ones: `125317Z` (old heuristic), `130022Z` (double-sigmoid).

---

## 4. Knobs you'll tune

| Knob | File | Effect |
|---|---|---|
| `RankWeights(relevance=1.0, temporal=0.3)` | `ranking.py` | Higher `temporal` floats recent entries up. Main dial now scoring is two-term. |
| `HALF_LIFE_DAYS = 90.0` | `ranking.py` | How fast old entries decay (90d = 3-month-old counts half). |
| `OVERSAMPLE = 4`, `MIN_POOL = 20` | `ranking.py` | How many candidates the cross-encoder sees. Bigger = better reranking, slower. |
| `MODEL_NAME` | `reranker.py` | Swap the cross-encoder. The plan says pick **one** decent model, don't A/B many. |
| `--top-k` | run_eval CLI | K for retrieval + metrics. |
| `_log_ranking` output | backend logs | Per-node `rel=… time=…` — read this to see *why* something ranked where it did. |

---

## 5. Iteration discipline (from the plan)

1. Change **one** knob.
2. `python run_eval.py` (off and/or on) → new run-folder.
3. Compare in `compare_runs.ipynb`.
4. Keep the change only if P@K / R@K / MRR beat noise.
5. Don't touch prompts until you can reproduce the same score **twice** on the same dataset.
6. DSPy only after the reranker is stable and reproducible.

---

## 6. Known gaps / gotchas

- **First reranker call downloads ~2 GB** (cached after). The first `--reranker` run and the first real app
  query will hang on it.
- **Metadata stamping is invisible on old data** — to test modality filtering, ingest a *fresh* source.
- **Eval Chroma ≠ app Chroma** — re-run `ingest.py` after any chunking change or you score stale chunks.
- **`raw.jsonl` stores pipe-joined strings** (`"N-1|N-2"`), not arrays — `metrics.parse_pipe` handles both.
- **Eval SQL isn't truly isolated** — we *neutralize* recency rather than spin up a separate DB. If you ever
  want to eval recency behaviour (e.g. the `stateful` set), give the eval its own SQLite instead of stubbing `get_sources_meta`.
- **Invalid early runs**: delete `results/20260604T125317Z_*` (old heuristic) and `20260604T130022Z_*`
  (double-sigmoid) — both predate the fixes.
