"""Ingest your own journals into an isolated Chroma collection for RAG testing.

Walks `journals/`, transcribes audio files via WhisperX, reads text/markdown
directly, chunks via the Backend chunker, and indexes into the isolated
`user_eval_chunks` collection. Wipes the collection before indexing so reruns
are reproducible.

Writes sources_index.json — a numeric source_id -> filename map used by
ask.py to show which journal each retrieved chunk came from.

Run: python ingest.py
"""
import _bootstrap

import json
import sys
from pathlib import Path

import strip_markdown

from app.schemas.journalSchemas import SimpleRecording
from app.services.chunking import chunk_text
from app.services.rag import configure_llamaindex, index_chunks

HERE = Path(__file__).resolve().parent
JOURNALS_DIR = HERE / "journals"
INDEX_MAP_PATH = HERE / "sources_index.json"

AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".webm", ".ogg"}
TEXT_EXTS = {".txt", ".md"}
SUPPORTED_EXTS = AUDIO_EXTS | TEXT_EXTS


def _read_text_file(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".md":
        text = strip_markdown.strip_markdown(text)
    return text


def _transcribe_audio(path: Path, source_id: int, transcriber) -> str:
    recording = SimpleRecording(path=str(path), id=str(source_id))
    transcript = transcriber.transcribe(recording)
    return transcript.text or ""


def main() -> int:
    JOURNALS_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(
        p for p in JOURNALS_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS and not p.name.startswith(".")
    )

    if not files:
        print(f"No journals found in {JOURNALS_DIR}", file=sys.stderr)
        print(f"Supported extensions: {', '.join(sorted(SUPPORTED_EXTS))}", file=sys.stderr)
        return 1

    print(f"Found {len(files)} journal file(s)")

    print("Resetting isolated Chroma collection...")
    _bootstrap.reset_chroma_collection()

    configure_llamaindex()

    transcriber = None
    has_audio = any(p.suffix.lower() in AUDIO_EXTS for p in files)
    if has_audio:
        print("Loading WhisperX transcription model (this can take a moment)...")
        from app.services.transcription import TranscriptionManager
        transcriber = TranscriptionManager()

    chunks: list[dict] = []
    chunk_id_counter = 1
    source_to_filename: dict[int, str] = {}

    for source_id, path in enumerate(files, start=1):
        ext = path.suffix.lower()
        try:
            if ext in AUDIO_EXTS:
                print(f"[{source_id}/{len(files)}] Transcribing {path.name}...", flush=True)
                text = _transcribe_audio(path, source_id, transcriber)
            else:
                print(f"[{source_id}/{len(files)}] Reading {path.name}...", flush=True)
                text = _read_text_file(path)
        except Exception as exc:
            print(f"    FAILED: {exc}", file=sys.stderr)
            continue

        if not text or not text.strip():
            print(f"    Skipping {path.name}: empty after read/transcription", file=sys.stderr)
            continue

        source_to_filename[source_id] = path.name
        file_chunks = chunk_text(text, source_id)
        for c in file_chunks:
            chunks.append({"id": chunk_id_counter, "text": c["text"], "source_id": source_id})
            chunk_id_counter += 1
        print(f"    -> {len(file_chunks)} chunk(s)")

    if not chunks:
        print("No chunks produced from any journal — nothing to index.", file=sys.stderr)
        return 1

    print(f"Produced {len(chunks)} chunks from {len(source_to_filename)} source(s)")
    print("Indexing into isolated Chroma...")
    index_chunks(chunks)

    INDEX_MAP_PATH.write_text(
        json.dumps({str(k): v for k, v in source_to_filename.items()}, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote source_id -> filename map to {INDEX_MAP_PATH}")
    print("Done. Run `python ask.py` to query your journals.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
