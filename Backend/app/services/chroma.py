from pathlib import Path

import chromadb

_client = None
_collection = None

CHROMA_PATH = Path(__file__).resolve().parent.parent.parent / "database" / "chroma"
CHROMA_PATH.mkdir(parents=True, exist_ok=True)
COLLECTION_NAME = "source_chunks"

def get_chroma_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _chunk_metadata(chunk: dict) -> dict:
    """Node metadata for a chunk; created_at_ts/modality stamped when present (Chroma rejects None)."""
    metadata = {"source_id": chunk["source_id"], "chunk_id": chunk["id"]}
    if chunk.get("created_at_ts") is not None:
        metadata["created_at_ts"] = int(chunk["created_at_ts"])
    if chunk.get("modality") is not None:
        metadata["modality"] = chunk["modality"]
    return metadata


def upsert_chunks(chunks: list[dict]):
    """
    chunks: list of {id, text, source_id, chunk_id, [created_at_ts], [modality]}
    Embeddings are handled by LlamaIndex, so we store raw docs here
    and let LlamaIndex manage the vector side via its ChromaVectorStore.
    This util is for direct upserts if needed outside LlamaIndex.
    """
    collection = get_chroma_collection()
    collection.upsert(
        ids=[str(c["id"]) for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[_chunk_metadata(c) for c in chunks],
    )