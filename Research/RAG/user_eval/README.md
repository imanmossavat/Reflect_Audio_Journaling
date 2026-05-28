# user_eval — bring-your-own-journals RAG sandbox

Created based of `maya_eval/`. Same idea (isolated Chroma collection, reuses the
Backend's chunker + RAG service), but pointed at **your own journals** so you
can spot-check answers against data you actually know.

The Chroma collection (`user_eval_chunks`) and DB path are completely
separate from production (`Backend/database/chroma/`) and from `maya_eval`.

## Setup

Drop your journal files into `journals/`. Supported extensions:

- Text: `.txt`, `.md`
- Audio: `.wav`, `.mp3`, `.m4a`, `.webm`, `.ogg` (transcribed via WhisperX)

The `journals/` and `chroma/` folders are gitignored — your private data
stays local.

## Run

```bash
# 1. Ingest: chunk + embed your journals into the isolated collection.
python ingest.py

# 2. Ask: interactive REPL. Type a question, see answer + sources. :q to quit.
python ask.py
```

Re-run `ingest.py` whenever you add, remove, or edit files in `journals/`, this wipes and rebuilds the collection so there are never stale or duplicate
chunks.

## Optional flags

- `python ask.py --top-k 10`, this is a setting to retrieve more (or less) sources per question (default 5).

## Files

| File | Purpose |
|------|---------|
| `_bootstrap.py` | Isolates Chroma to `user_eval/chroma/` + collection `user_eval_chunks` before any RAG import. |
| `ingest.py` | Walks `journals/`, transcribes audio + reads text, chunks, indexes. |
| `ask.py` | Interactive REPL: question → answer + which journals it came from. |
| `sources_index.json` | Generated. Maps numeric source_id back to your filename. |
| `journals/` | Drop your files here. Gitignored. |
| `chroma/` | Generated vector DB. Gitignored. |
