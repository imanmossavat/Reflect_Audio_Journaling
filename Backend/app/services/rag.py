import shutil

import httpx
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.core.schema import TextNode
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.core.prompts import PromptTemplate

from typing import Any

from app.services.chroma import get_chroma_collection
from app.services.settings_service import get_setting


def _ollama_base_url() -> str:
    return get_setting("ollama_host").rstrip("/")


def _embed_model() -> str:
    return get_setting("embed_model")


def _llm_model() -> str:
    return get_setting("chat_model")


# Module-level `from app.services.rag import EMBED_MODEL, LLM_MODEL, OLLAMA_BASE_URL`
# still works — these names resolve lazily through module __getattr__.
def __getattr__(name: str) -> Any:
    if name == "OLLAMA_BASE_URL":
        return _ollama_base_url()
    if name == "EMBED_MODEL":
        return _embed_model()
    if name == "LLM_MODEL":
        return _llm_model()
    raise AttributeError(f"module 'app.services.rag' has no attribute {name!r}")


def check_ollama_state() -> str:
    """Returns 'ok', 'not_running', or 'not_installed'."""
    try:
        with httpx.Client(timeout=3.0) as client:
            client.get(_ollama_base_url())
        return "ok"
    except httpx.ConnectError:
        return "not_running" if shutil.which("ollama") else "not_installed"
    except Exception:
        return "not_running"


def check_model_installed(model: str) -> bool:
    """Returns True if the given model appears in `ollama list`. Assumes Ollama is reachable."""
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{_ollama_base_url()}/api/tags")
            response.raise_for_status()
            installed = {m.get("name", "") for m in response.json().get("models", [])}
        # Ollama lists models as e.g. "nomic-embed-text:latest"; accept either exact or bare-name match.
        return any(name == model or name.startswith(f"{model}:") for name in installed)
    except Exception:
        return True  # Best-effort: don't block on the precheck if /api/tags is unreachable.


def classify_ollama_error(exc: Exception) -> str:
    """Returns 'not_running', 'model_missing', or 'unknown' based on the exception."""
    msg = str(exc).lower()
    connection_markers = (
        "connection refused",
        "11434",
        "all connection attempts failed",
        "winerror 10061",
        "connecterror",
        "connect call failed",
        "connection error",
        "remoteprotocolerror",
        "max retries exceeded",
    )
    if any(marker in msg for marker in connection_markers):
        return "not_running"
    if "not found" in msg or "try pulling" in msg or "pull it first" in msg or "no such model" in msg:
        return "model_missing"
    return "unknown"

TEXT_QA_TEMPLATE = PromptTemplate(
    "Context information is below.\n"
    "---------------------\n"
    "{context_str}\n"
    "---------------------\n"
    "Using the context above, answer the following question.\n"
    "Always use 'you' and 'your' in your response. "
    "Do NOT use 'I' or 'me'.\n"
    "Question: {query_str}\n"
    "Answer: "
)

_llamaindex_signature: tuple[str, str, str] | None = None


def configure_llamaindex() -> None:
    """Configure LlamaIndex globals from current settings. Re-runs when settings change."""
    global _llamaindex_signature
    embed = _embed_model()
    llm = _llm_model()
    host = _ollama_base_url()
    signature = (embed, llm, host)
    if _llamaindex_signature == signature:
        return
    Settings.embed_model = OllamaEmbedding(
        model_name=embed,
        base_url=host,
    )
    Settings.llm = Ollama(
        model=llm,
        base_url=host,
        request_timeout=120.0,
        temperature=0.0,
    )
    _llamaindex_signature = signature


configure_llamaindex()


def _get_index() -> VectorStoreIndex:
    collection = get_chroma_collection()
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    return VectorStoreIndex.from_vector_store(
        vector_store, storage_context=storage_context
    )

def index_chunks(chunks: list[dict]):
    configure_llamaindex()
    collection = get_chroma_collection()
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    nodes = [
        TextNode(
            text=c["text"],
            id_=str(c["id"]),
            metadata={"source_id": c["source_id"], "chunk_id": c["id"]},
        )
        for c in chunks
    ]

    VectorStoreIndex(nodes, storage_context=storage_context)

def query_sources(question: str, top_k: int = 5) -> dict[str, Any]:
    configure_llamaindex()
    index = _get_index()
    query_engine = index.as_query_engine(similarity_top_k=top_k, text_qa_template=TEXT_QA_TEMPLATE,)
    print(f"Querying with question: {question}")
    response = query_engine.query(question)
    answer_text = response.response

    sources = []
    for source in getattr(response, "source_nodes", []) or []:
        node = source.node
        metadata = node.metadata or {}
        sources.append(
            {
                "source_id": metadata.get("source_id"),
                "chunk_id": metadata.get("chunk_id"),
                "score": source.score,
                "node_id": node.node_id,
                "text": node.get_content(),
            }
        )

    return {
        "answer": answer_text,
        "sources": sources,
    }