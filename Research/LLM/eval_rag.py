import os, json
import pandas as pd
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, PromptTemplate
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core import Settings
from ragas.metrics.collections import Faithfulness, AnswerRelevancy, ContextPrecision
from ragas import evaluate
from datasets import Dataset



import argparse
import json
from pathlib import Path
from typing import Any


# ── config ────────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = "http://localhost:11434"
EVAL_DATA_PATH  = "./eval_data"
RESULTS_PATH    = "./eval_results"
EMBED_MODEL     = "nomic-embed-text"
TESTSET_MODEL   = "mistral"   # model used to generate QA pairs — fixed for consistency
TESTSET_SIZE    = 20

MODELS_TO_TEST = [
    "mistral",
    "qwen3.5:4b",
    "llama3",
]

REFLECT_QA_PROMPT = PromptTemplate(
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
# ─────────────────────────────────────────────────────────────────────────────

os.makedirs(RESULTS_PATH, exist_ok=True)

documents = SimpleDirectoryReader(EVAL_DATA_PATH).load_data()
print(f"Loaded {len(documents)} documents")


def build_llm(model_name: str) -> Ollama:
    extra = {"think": False} if "qwen" in model_name.lower() else {}
    return Ollama(
        model=model_name,
        base_url=OLLAMA_BASE_URL,
        request_timeout=180.0,
        additional_kwargs=extra,
    )


def build_embed() -> OllamaEmbedding:
    return OllamaEmbedding(model_name=EMBED_MODEL, base_url=OLLAMA_BASE_URL)


def generate_testset(llm: Ollama) -> list[dict]:
    """
    Generate QA pairs from journal documents using a plain Ollama call.
    Avoids RAGAS TestsetGenerator which breaks with local models due to
    internal Pydantic structured output parsing.
    """
    all_text = "\n\n---\n\n".join(
        [f"Entry {i+1}:\n{doc.text}" for i, doc in enumerate(documents)]
    )

    prompt = f"""You are building an evaluation dataset for a RAG system over personal journal entries.

Given the journal entries below, generate {TESTSET_SIZE} question-answer pairs.

Rules:
- Questions must be answerable from the journal content
- Questions should be varied: some about specific events, some about recurring themes, some about emotions
- Answers should be grounded in the text, 1-3 sentences
- Return only valid JSON — an array of objects with keys "question" and "ground_truth"
- No preamble, no explanation, just the JSON array

Journal entries:
{all_text}

JSON:"""

    raw = str(llm.complete(prompt)).strip()

    # strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        pairs = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("[")
        end   = raw.rfind("]") + 1
        pairs = json.loads(raw[start:end])

    print(f"Generated {len(pairs)} QA pairs")
    return pairs


def build_index(llm: Ollama) -> VectorStoreIndex:
    embed = build_embed()
    Settings.llm         = llm
    Settings.embed_model = embed
    return VectorStoreIndex.from_documents(documents)


def run_rag(index: VectorStoreIndex, questions: list[str]) -> list[dict]:
    query_engine = index.as_query_engine(
        similarity_top_k=5,
        text_qa_template=REFLECT_QA_PROMPT,
    )
    rows = []
    for q in questions:
        response = query_engine.query(q)
        rows.append({
            "question": q,
            "answer":   str(response),
            "contexts": [node.get_content() for node in response.source_nodes],
        })
    return rows


def score_rag(rag_results: list[dict], testset: list[dict]) -> pd.DataFrame:
    ground_truths = {item["question"]: item["ground_truth"] for item in testset}
    for row in rag_results:
        row["ground_truth"] = ground_truths.get(row["question"], "")

    ds     = Dataset.from_list(rag_results)
    result = evaluate(ds, metrics=[Faithfulness(), AnswerRelevancy(), ContextPrecision()])
    return result.to_pandas()


# ── generate testset once, reuse across all models ────────────────────────────
print(f"Generating testset with {TESTSET_MODEL}...")
testset_llm = build_llm(TESTSET_MODEL)
"""
RAG answer quality eval for REFLECT.

This intentionally avoids auto-generated Ragas testsets because local Ollama
models are often brittle on strict parser prompts and can fail mid-run.

Flow:
1. Retrieve top-k chunks per query from the journal corpus.
2. Ask each model to answer using only retrieved context.
3. Use a fixed judge model to score harshly on:
   - faithfulness
   - answer_relevancy
   - context_precision
4. Save per-example and per-model summaries.
"""





# ── config ────────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = "http://localhost:11434"
SCRIPT_DIR = Path(__file__).resolve().parent
EVAL_DATA_PATH = SCRIPT_DIR / "eval_data"
RESULTS_PATH = SCRIPT_DIR / "eval_results"

EMBED_MODEL = "nomic-embed-text"
DEFAULT_TOP_K = 5

MODELS_TO_TEST = [
    "mistral",
    "llama3",
]

TEST_QUERIES = [
    "What recurring patterns appear in how I handle work stress?",
    "What does my relationship with productivity look like?",
    "How do I talk about my relationships with other people?",
    "What themes come up when I am having a low energy day?",
    "What am I avoiding or procrastinating on?",
    "Where do I sound conflicted between values and actions?",
    "What tradeoffs keep appearing in my decisions?",
]

ANSWER_PROMPT = """You are an evidence-grounded reflection assistant.

Answer the user's question using only the retrieved journal context.
If context is insufficient, say what is missing instead of inventing details.

Question:
{query}

Retrieved context:
{context}

Answer:"""

JUDGE_PROMPT = """You are grading a RAG answer. Be strict and unsparing.
Respond only with valid JSON, no extra text.

Question:
{query}

Retrieved context:
{context}

Model answer:
{answer}

Score each 1-5:
- faithfulness: every claim is supported by retrieved context; penalize invented details hard.
- answer_relevancy: directly answers the question without vague filler.
- context_precision: uses relevant context points, not generic statements disconnected from evidence.

{{"faithfulness": N, "answer_relevancy": N, "context_precision": N, "reason": "one sentence"}}"""


# ── helpers ───────────────────────────────────────────────────────────────────
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run harsh RAG answer evaluation.")
    parser.add_argument("--models", nargs="+", default=MODELS_TO_TEST, help="Ollama models to evaluate.")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="Retriever top-k chunks.")
    parser.add_argument("--max-queries", type=int, default=None, help="Optional cap for quick smoke tests.")
    parser.add_argument("--judge-model", default="mistral", help="Fixed model used for grading.")
    parser.add_argument("--request-timeout", type=float, default=120.0, help="Request timeout in seconds.")
    return parser.parse_args()


def build_llm(model_name: str, request_timeout: float) -> Ollama:
    extra = {"think": False} if "qwen" in model_name.lower() else {}
    return Ollama(
        model=model_name,
        base_url=OLLAMA_BASE_URL,
        request_timeout=request_timeout,
        additional_kwargs=extra,
    )


def load_documents() -> list[Any]:
    if not EVAL_DATA_PATH.exists():
        raise FileNotFoundError(f"eval_data directory not found: {EVAL_DATA_PATH}")
    documents = SimpleDirectoryReader(str(EVAL_DATA_PATH)).load_data()
    if not documents:
        raise ValueError(f"No documents found in: {EVAL_DATA_PATH}")
    return documents


def build_index(documents: list[Any], embed: OllamaEmbedding) -> VectorStoreIndex:
    return VectorStoreIndex.from_documents(documents, embed_model=embed)


def retrieve_context(index: VectorStoreIndex, query: str, top_k: int) -> tuple[str, list[str]]:
    retriever = index.as_retriever(similarity_top_k=top_k)
    nodes = retriever.retrieve(query)
    chunks = [n.get_content() for n in nodes]
    context = "\n\n---\n\n".join(chunks)
    return context, chunks


def generate_answer(llm: Ollama, query: str, context: str) -> str:
    prompt = ANSWER_PROMPT.format(query=query, context=context)
    return str(llm.complete(prompt)).strip()


def parse_json_dict(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end <= start:
            return {}
        try:
            parsed = json.loads(raw[start:end])
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}


def to_score(value: Any) -> int | None:
    try:
        score = int(value)
    except (TypeError, ValueError):
        return None
    return max(1, min(5, score))


def judge_answer(judge_llm: Ollama, query: str, context: str, answer: str) -> dict[str, Any]:
    prompt = JUDGE_PROMPT.format(query=query, context=context, answer=answer)
    raw = str(judge_llm.complete(prompt)).strip()
    return parse_json_dict(raw)


# ── main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    args = parse_args()
    RESULTS_PATH.mkdir(parents=True, exist_ok=True)

    documents = load_documents()
    embed = OllamaEmbedding(model_name=EMBED_MODEL, base_url=OLLAMA_BASE_URL)
    queries = TEST_QUERIES[: args.max_queries] if args.max_queries else TEST_QUERIES

    if not queries:
        raise ValueError("No queries selected for evaluation.")

    print(f"Loaded {len(documents)} documents")
    print(f"Evaluating {len(args.models)} model(s) across {len(queries)} query/queries")

    judge_llm = build_llm(args.judge_model, args.request_timeout)
    rows: list[dict[str, Any]] = []

    for model_name in args.models:
        print(f"\n-- evaluating {model_name} --")
        llm = build_llm(model_name, args.request_timeout)
        index = build_index(documents, embed)

        for query in queries:
            context, chunks = retrieve_context(index, query, args.top_k)
            answer = generate_answer(llm, query, context)
            scores = judge_answer(judge_llm, query, context, answer)

            print(f"  query: {query[:70]}...")
            print(f"  answer: {answer[:100]}{'...' if len(answer) > 100 else ''}")

            rows.append(
                {
                    "model": model_name,
                    "query": query,
                    "retrieved_chunks": len(chunks),
                    "answer": answer,
                    "faithfulness": to_score(scores.get("faithfulness")),
                    "answer_relevancy": to_score(scores.get("answer_relevancy")),
                    "context_precision": to_score(scores.get("context_precision")),
                    "reason": scores.get("reason"),
                }
            )

    df = pd.DataFrame(rows)
    metric_cols = ["faithfulness", "answer_relevancy", "context_precision"]
    summary = (
        df.groupby("model")[metric_cols]
        .mean(numeric_only=True)
        .round(3)
        .sort_values(metric_cols, ascending=False)
    )

    per_example_path = RESULTS_PATH / "rag_eval.csv"
    summary_path = RESULTS_PATH / "rag_eval_summary.csv"
    df.to_csv(per_example_path, index=False)
    summary.to_csv(summary_path)

    print("\n-- rag summary --")
    print(summary)
    print(f"\nSaved -> {per_example_path}")
    print(f"Saved -> {summary_path}")


if __name__ == "__main__":
    main()