# Maya synthetic RAG eval

Testing/benchmarking of the RAG against a journal where supporting notes and entities are known per question.

The goal isn't a single score, it's to answer **"these questions go wrong, and in this sense"** for each failing item:
- retrieval miss vs. partial retrieval
- generation overreach (adds psychology not in notes)
- hallucination (invents facts)
- failed refusal (fabricates instead of saying "I don't know")
- incorrect refusal (refuses when the answer is right there)

## Isolation

The eval uses its own Chroma DB at `chroma/` and its own collection `maya_eval_chunks`. `_bootstrap.py` uses `app.services.chroma` before any rag code runs, so production embeddings at `Backend/database/chroma/` are never touched.

The eval still uses real settings (chat_model, embed_model, ollama_host from `Backend/data/settings.json`) — point is to test the *real* RAG, just with isolated storage.

## Run

Ollama must be running with the chat + embed models configured in the backend.

```powershell
python generate_notes.py     # one-time; writes notes.json (~32 notes)
python ingest.py             # resets chroma/ and rebuilds the index
python run_eval.py           # writes results/raw.csv + raw.jsonl
python judge.py              # writes results/judged.csv
python report.py             # prints summary + writes results/summary.csv
```

Regenerate notes: `python generate_notes.py --force`.

## Files

| file | purpose |
|---|---|
| `_bootstrap.py` | sys.path + Chroma isolation; import FIRST |
| `world_state.json` | Maya world state (lifted from the pipeline doc) |
| `generate_notes.py` | pre-scripted events expanded into prose by Ollama |
| `notes.json` | generated note corpus (committed for reproducibility once stable) |
| `questions.json` | 20 questions from the doc + 5 unanswerable |
| `ingest.py` | chunks + indexes notes into isolated Chroma |
| `notes_index.json` | source_id (numeric) -> note_id (e.g. N-7811) map |
| `run_eval.py` | runs each question through `rag.query_sources` |
| `judge.py` | LLM-as-judge → failure-mode label + rationale |
| `report.py` | counts per failure mode + per-question table |

## Failure-mode taxonomy

- **CORRECT** — answer supported, or a proper refusal for unanswerable.
- **RETRIEVAL_MISS** — none of the gold notes made it into top-k.
- **PARTIAL_RETRIEVAL** — some gold notes retrieved; answer missing the rest.
- **GENERATION_OVERREACH** — right notes retrieved, answer over-infers psychology/causality.
- **GENERATION_HALLUCINATION** — answer states a fact not in any retrieved chunk.
- **FAILED_REFUSAL** — question unanswerable but RAG fabricated an answer.
- **INCORRECT_REFUSAL** — answer was in retrieved context but RAG refused.
- **CONTRADICTS_NOTES** — answer states something the notes explicitly contradict.
