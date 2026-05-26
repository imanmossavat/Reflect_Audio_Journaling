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


# WARNING: `from app.services.rag import EMBED_MODEL` binds the value at import time
# and won't reflect later settings changes. Use `rag.EMBED_MODEL` (module attribute access)
# or call get_setting() directly where a fresh value is needed.
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


_thinking_capability_cache: dict[tuple[str, str], bool] = {}


def model_supports_thinking(model: str) -> bool:
    """Returns True if Ollama reports the model has the 'thinking' capability.

    Cached per (host, model) for the lifetime of the process — a model's capabilities
    don't change without a re-pull, and the user can restart the backend to refresh.
    """
    host = _ollama_base_url()
    key = (host, model)
    if key in _thinking_capability_cache:
        return _thinking_capability_cache[key]
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.post(f"{host}/api/show", json={"model": model})
            r.raise_for_status()
            supports = "thinking" in (r.json().get("capabilities") or [])
    except Exception:
        supports = False
    _thinking_capability_cache[key] = supports
    return supports


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

def retrieve_nodes(question: str, top_k: int = 5) -> list[Any]:
    """Returns the top_k retrieved nodes for `question` without running the LLM step."""
    configure_llamaindex()
    index = _get_index()
    retriever = index.as_retriever(similarity_top_k=top_k)
    return retriever.retrieve(question)


def serialize_retrieved_nodes(nodes: list[Any]) -> list[dict[str, Any]]:
    """Serialize retriever results into the same shape `query_sources` returns under `sources`."""
    sources = []
    for source in nodes or []:
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
    return sources


def build_context_str(nodes: list[Any]) -> str:
    """Join retrieved node texts into the `{context_str}` block for TEXT_QA_TEMPLATE."""
    return "\n\n".join((source.node.get_content() or "").strip() for source in nodes or [])


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