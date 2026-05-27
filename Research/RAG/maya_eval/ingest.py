"""Chunk and index the Maya notes into the isolated Chroma collection.

Reuses Backend chunking + rag.index_chunks. Wipes the eval collection
before indexing so runs are reproducible.

Writes notes_index.json — a numeric source_id -> note_id map used by
run_eval.py to translate retrieved source_ids back to note_ids.

Run: python ingest.py
"""
import _bootstrap

import json
import sys
from pathlib import Path

from app.services.chunking import chunk_text
from app.services.rag import index_chunks, configure_llamaindex

HERE = Path(__file__).resolve().parent
NOTES_PATH = HERE / "notes.json"
INDEX_MAP_PATH = HERE / "notes_index.json"


def main() -> int:
    if not NOTES_PATH.exists():
        print(f"{NOTES_PATH} not found. Run generate_notes.py first.", file=sys.stderr)
        return 1

    notes = json.loads(NOTES_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(notes)} notes")

    print("Resetting isolated Chroma collection...")
    _bootstrap.reset_chroma_collection()

    configure_llamaindex()

    chunks: list[dict] = []
    chunk_id_counter = 1
    source_to_note: dict[int, str] = {}

    for source_id, note in enumerate(notes, start=1):
        source_to_note[source_id] = note["note_id"]
        # chunk_text returns [{text, source_id}, ...]; assign chunk_ids ourselves.
        for c in chunk_text(note["text"], source_id):
            chunks.append({"id": chunk_id_counter, "text": c["text"], "source_id": source_id})
            chunk_id_counter += 1

    print(f"Produced {len(chunks)} chunks from {len(notes)} notes")
    print("Indexing into isolated Chroma...")
    index_chunks(chunks)

    INDEX_MAP_PATH.write_text(
        json.dumps({str(k): v for k, v in source_to_note.items()}, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote source_id -> note_id map to {INDEX_MAP_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
