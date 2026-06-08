# Synthetic RAG eval

Benchmarking the production RAG against synthetic journals where the supporting notes and
entities are **known per question**. The goal isn't a single score — it's to answer
**"these questions go wrong, and in this sense"** for each failing item:
- retrieval miss vs. partial retrieval
- generation overreach (adds psychology/state not in notes)
- hallucination (invents facts)
- failed refusal (fabricates instead of saying "I don't know")
- incorrect refusal (refuses when the answer is right there)

## Layout

```
eval/
  harness/              persona-agnostic code (run scripts from here)
    _bootstrap.py         sys.path + PER-DATASET Chroma isolation; import FIRST
    ingest.py             chunk + index a dataset's notes  (--dataset)
    run_eval.py           run questions through the real RAG (--dataset, --questions, --reranker)
    metrics.py            deterministic retrieval metrics (P@K, R@K, MRR) over a run folder
    judge.py              LLM-as-judge → failure-mode label + rationale
    report.py             counts per failure mode + per-question table
    compare_runs.ipynb    plot metrics across runs
  datasets/
    baseline/             the "easy" Maya set — most answers are a single note
      world_state.json  notes.json  questions.json  questions_multi.json  notes_index.json  generate.py
    stateful/             the hard Niels set — states evolve; current/former/prospective; multi-hop
      world_state.json  notes.json  questions.json  generate.py
  runs/<dataset>/<ts>_<hash>/   per-run outputs (gitignored)
  chroma/<dataset>/             isolated vector store per dataset (gitignored)
  _archive/                     legacy run artifacts
```

Each dataset is self-contained and uses identical internal filenames, so the harness is
driven entirely by `--dataset <name>`. Add a new dataset = add a `datasets/<name>/` folder.

## Isolation

`_bootstrap.use_dataset(name)` points `app.services.chroma` at `chroma/<name>/` with collection
`<name>_chunks`, so (a) production embeddings at `Backend/database/chroma/` are never touched and
(b) `baseline` and `stateful` never share a collection. The eval still uses the **real** settings
(chat_model, embed_model, ollama_host from `Backend/data/settings.json`) — it tests the real RAG,
just with isolated storage.

## Run

Ollama must be running with the chat + embed models configured in the backend. Run from `eval/`:

```powershell
python datasets/stateful/generate.py            # writes datasets/stateful/notes.json (--raw to skip LLM)
python harness/ingest.py    --dataset stateful  # resets chroma/stateful/ and rebuilds the index
python harness/run_eval.py  --dataset stateful  # writes runs/stateful/<ts>/raw.{csv,jsonl} + summary.csv
python harness/run_eval.py  --dataset stateful --reranker
python harness/judge.py     --results-dir runs/stateful/<ts>_<hash>
python harness/report.py    --results-dir runs/stateful/<ts>_<hash>
```

Baseline is the same with `--dataset baseline` (and `--questions questions_multi.json` for the
multi-note variant).

## Failure-mode taxonomy

- **CORRECT** — answer supported, or a proper refusal for unanswerable.
- **RETRIEVAL_MISS** — none of the gold notes made it into top-k.
- **PARTIAL_RETRIEVAL** — some gold notes retrieved; answer missing the rest.
- **GENERATION_OVERREACH** — right notes retrieved, answer over-infers psychology/causality/state.
- **GENERATION_HALLUCINATION** — answer states a fact not in any retrieved chunk.
- **FAILED_REFUSAL** — question unanswerable but RAG fabricated an answer.
- **INCORRECT_REFUSAL** — answer was in retrieved context but RAG refused.
- **CONTRADICTS_NOTES** — answer states something the notes explicitly contradict.

## Datasets at a glance

| | baseline (Maya) | stateful (Niels) |
|---|---|---|
| notes | 22 | 34 |
| questions | single-note + multi-note variant | 18, hop-graded (1–5 hops) |
| tests | retrieval + grounding fidelity | **state resolution**: current vs former vs prospective, multi-hop, recency-vs-relevance traps |
| answer key | per-question gold notes | `world_state.json` state-variable timelines (validity intervals) |

See `GUIDE.md` for the metadata→eval→reranker history and how to read the numbers.
