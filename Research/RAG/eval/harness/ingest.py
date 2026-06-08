"""Chunk and index a dataset's notes into its isolated Chroma collection.

Reuses Backend chunking + rag.index_chunks. Writes datasets/<dataset>/notes_index.json
-- a numeric source_id -> note_id map used by run_eval.py to translate retrieved
source_ids back to note_ids.

Run:  python harness/ingest.py --dataset baseline
      python harness/ingest.py --dataset stateful
"""
import _bootstrap

import argparse
import json
import sys

from app.services.chunking import chunk_text
from app.services.rag import index_chunks, configure_llamaindex


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="baseline",
                        help=f"dataset name under datasets/ (have: {', '.join(_bootstrap.list_datasets()) or 'none'})")
    args = parser.parse_args()

    paths = _bootstrap.use_dataset(args.dataset)
    notes_path, index_path = paths["notes"], paths["index"]

    if not notes_path.exists():
        print(f"{notes_path} not found. Run datasets/{args.dataset}/generate.py first.", file=sys.stderr)
        return 1

    notes = json.loads(notes_path.read_text(encoding="utf-8"))
    print(f"[{args.dataset}] Loaded {len(notes)} notes")

    print(f"Resetting isolated Chroma collection '{args.dataset}_chunks'...")
    _bootstrap.reset_chroma_collection()

    configure_llamaindex()

    chunks: list[dict] = []
    chunk_id_counter = 1
    source_to_note: dict[int, str] = {}

    for source_id, note in enumerate(notes, start=1):
        source_to_note[source_id] = note["note_id"]
        for c in chunk_text(note["text"], source_id):
            chunks.append({"id": chunk_id_counter, "text": c["text"], "source_id": source_id})
            chunk_id_counter += 1

    print(f"Produced {len(chunks)} chunks from {len(notes)} notes")
    print("Indexing into isolated Chroma...")
    index_chunks(chunks)

    index_path.write_text(
        json.dumps({str(k): v for k, v in source_to_note.items()}, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote source_id -> note_id map to {index_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
