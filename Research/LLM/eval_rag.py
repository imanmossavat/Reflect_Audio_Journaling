"""
RAG answer quality eval for REFLECT.

Flow:
1. Retrieve top-k chunks per query from the journal corpus.
2. Ask each model to answer using only retrieved context.
3. Aggregate one or more judge-model scores for answer quality.
4. Save per-example and per-model summaries.
"""

import argparse
import json
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

import pandas as pd
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama



SCRIPT_DIR = Path(__file__).resolve().parent
EVAL_DATA_PATH = SCRIPT_DIR / "eval_data"
RESULTS_PATH = SCRIPT_DIR / "eval_results"

OLLAMA_BASE_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"

MODELS_TO_TEST = ["mistral", "llama3", "gpt-oss:20b"]
JUDGE_MODELS = ["mistral", "llama3"]
DEFAULT_TOP_K = 5

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

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run RAG answer benchmark.")
    parser.add_argument("--models", nargs="+", default=MODELS_TO_TEST, help="Generator models to evaluate.")
    parser.add_argument("--judge-models", nargs="+", default=JUDGE_MODELS, help="Judge models for score aggregation.")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="Retriever top-k chunks.")
    parser.add_argument("--max-queries", type=int, default=None, help="Optional cap for quick smoke tests.")
    parser.add_argument("--request-timeout", type=float, default=120.0, help="Ollama request timeout in seconds.")
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
    chunks = [node.get_content() for node in nodes]
    context = "\n\n---\n\n".join(chunks)
    return context, chunks


def generate_answer(llm: Ollama, query: str, context: str) -> str:
    prompt = ANSWER_PROMPT.format(query=query, context=context)
    return str(llm.complete(prompt)).strip()


def extract_json_dict(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end <= start:
            return {}
        try:
            parsed = json.loads(text[start:end])
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
    return extract_json_dict(raw)


def aggregate_judgements(judge_payloads: dict[str, dict[str, Any]]) -> dict[str, Any]:
    metrics = ("faithfulness", "answer_relevancy", "context_precision")
    per_judge_scores: dict[str, dict[str, int | None]] = {}
    reasons: list[str] = []
    valid_count = 0

    for judge_name, payload in judge_payloads.items():
        row_scores = {metric: to_score(payload.get(metric)) for metric in metrics}
        per_judge_scores[judge_name] = row_scores

        if any(value is not None for value in row_scores.values()):
            valid_count += 1

        reason = payload.get("reason")
        if isinstance(reason, str) and reason.strip():
            reasons.append(f"{judge_name}: {reason.strip()}")

    aggregated: dict[str, Any] = {}
    for metric in metrics:
        values = [
            row[metric]
            for row in per_judge_scores.values()
            if row[metric] is not None
        ]
        aggregated[metric] = round(mean(values), 3) if values else None
        if not values:
            aggregated[f"{metric}_judge_std"] = None
        elif len(values) == 1:
            aggregated[f"{metric}_judge_std"] = 0.0
        else:
            aggregated[f"{metric}_judge_std"] = round(pstdev(values), 3)

    judge_count = max(1, len(judge_payloads))
    aggregated["judge_valid_count"] = valid_count
    aggregated["judge_valid_rate"] = round(valid_count / judge_count, 3)
    aggregated["judge_reasons"] = " | ".join(reasons)
    aggregated["judge_scores_json"] = json.dumps(per_judge_scores, ensure_ascii=True)
    return aggregated



def main() -> None:
    args = parse_args()
    RESULTS_PATH.mkdir(parents=True, exist_ok=True)

    documents = load_documents()
    embed = OllamaEmbedding(model_name=EMBED_MODEL, base_url=OLLAMA_BASE_URL)
    index = build_index(documents, embed)
    queries = TEST_QUERIES[: args.max_queries] if args.max_queries else TEST_QUERIES

    if not queries:
        raise ValueError("No queries selected for evaluation.")

    judge_llms = {
        judge_name: build_llm(judge_name, args.request_timeout)
        for judge_name in args.judge_models
    }

    print(f"Loaded {len(documents)} documents")
    print(f"Evaluating {len(args.models)} generator model(s) across {len(queries)} query/queries")
    print(f"Using {len(judge_llms)} judge model(s): {', '.join(judge_llms.keys())}")

    rows: list[dict[str, Any]] = []
    for model_name in args.models:
        print(f"\n-- evaluating {model_name} --")
        generator_llm = build_llm(model_name, args.request_timeout)

        for query in queries:
            context, chunks = retrieve_context(index, query, args.top_k)
            answer = generate_answer(generator_llm, query, context)

            judge_payloads: dict[str, dict[str, Any]] = {}
            for judge_name, judge_llm in judge_llms.items():
                judge_payloads[judge_name] = judge_answer(judge_llm, query, context, answer)

            aggregate = aggregate_judgements(judge_payloads)

            print(f"  query: {query[:70]}...")
            print(f"  answer: {answer[:100]}{'...' if len(answer) > 100 else ''}")

            rows.append(
                {
                    "model": model_name,
                    "query": query,
                    "retrieved_chunks": len(chunks),
                    "answer": answer,
                    **aggregate,
                }
            )

    df = pd.DataFrame(rows)
    summary = (
        df.groupby("model")
        .agg(
            samples=("answer", "count"),
            faithfulness=("faithfulness", "mean"),
            answer_relevancy=("answer_relevancy", "mean"),
            context_precision=("context_precision", "mean"),
            judge_valid_rate=("judge_valid_rate", "mean"),
        )
        .round(3)
        .sort_values(
            ["faithfulness", "answer_relevancy", "context_precision"],
            ascending=False,
        )
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