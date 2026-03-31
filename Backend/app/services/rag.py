from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.core.schema import TextNode
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.core.prompts import PromptTemplate

from typing import Any

from app.services.chroma import get_chroma_collection

OLLAMA_BASE_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
LLM_MODEL = "gpt-oss:20b"

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

# Configure LlamaIndex globals once
Settings.embed_model = OllamaEmbedding(
    model_name=EMBED_MODEL,
    base_url=OLLAMA_BASE_URL,
)
Settings.llm = Ollama(
    model=LLM_MODEL,
    base_url=OLLAMA_BASE_URL,
    request_timeout=120.0,
    temperature=0.0
)


def _get_index() -> VectorStoreIndex:
    collection = get_chroma_collection()
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    return VectorStoreIndex.from_vector_store(
        vector_store, storage_context=storage_context
    )

def index_chunks(chunks: list[dict]):
    collection = get_chroma_collection()
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    nodes = [
        TextNode(
            text=c["text"],
            id_=str(c["id"]),
            metadata={"journal_id": c["journal_id"], "chunk_id": c["id"]},
        )
        for c in chunks
    ]

    VectorStoreIndex(nodes, storage_context=storage_context)

def query_journals(question: str, top_k: int = 5) -> dict[str, Any]:
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
                "journal_id": metadata.get("journal_id"),
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