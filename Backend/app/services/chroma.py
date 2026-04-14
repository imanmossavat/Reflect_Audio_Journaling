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


def upsert_chunks(chunks: list[dict]):
    """
    chunks: list of {id, text, source_id, chunk_id}
    Embeddings are handled by LlamaIndex, so we store raw docs here
    and let LlamaIndex manage the vector side via its ChromaVectorStore.
    This util is for direct upserts if needed outside LlamaIndex.
    """
    collection = get_chroma_collection()
    collection.upsert(
        ids=[str(c["id"]) for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[{"source_id": c["source_id"], "chunk_id": c["id"]} for c in chunks],
    )