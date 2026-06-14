"""Run one RAG experiment end-to-end and produce a consistent evaluation output.

Plug-and-play: the retriever, prompt, and generator model are selected by an
`ExperimentConfig` and **injected** into the production pipeline — no monkeypatching.
Swap any one of them and re-run; the rest of the pipeline is untouched.

    python harness/run_experiment.py --dataset stateful --prompt default --no-reranker
    python harness/run_experiment.py --dataset stateful --prompt strict_refusal --no-reranker
    python harness/run_experiment.py --dataset stateful --reranker --thinking --chat-model gemma4:26b
    python harness/run_experiment.py --config my_experiment.json

Writes runs/<dataset>/<ts>_<hash>/ with raw.{csv,jsonl} + config.json, then scores it
via evaluation.evaluate (summary.csv + answers.csv). Ingest the dataset first:
    python harness/ingest.py --dataset stateful
"""
import _bootstrap

import argparse
import csv
import json
import subprocess
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path

import evaluation
from app.services import retrieval, generation, llm_runtime
from app.services.prompt import get_prompt
from app.services.ranking import DEFAULT_WEIGHTS, RankWeights
from app.services.settings_service import get_setting
from llama_index.core import Settings
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama


@dataclass
class ExperimentConfig:
    """Everything that defines an experiment. Each field is an independent lever."""
    dataset: str = "stateful"
    top_k: int = 5
    reranker: bool = True
    prompt: str = "default"            # name in app.services.prompt.PROMPTS
    chat_model: str | None = None      # None -> settings.json chat_model
    embed_model: str | None = None     # None -> settings.json embed_model (must match the ingested collection)
    thinking: bool = False
    questions: str = "questions.json"
    weights: RankWeights = field(default_factory=lambda: DEFAULT_WEIGHTS)


# --------------------------------------------------------------------------- component wiring

def build_retriever(cfg: ExperimentConfig):
    """A retrieve_fn(question, top_k, modality) with cfg's reranker/recency/weights injected.

    Eval isolation: synthetic source_ids collide with real SQLite rows, so we neutralize
    recency (source_meta_provider -> {}). Reranker OFF = identity rerank (embedding score)."""
    reranker_fn = None if cfg.reranker else retrieval._identity_rerank

    def retrieve_fn(question, top_k=cfg.top_k, modality=None):
        return retrieval.ranked_retrieve(
            question,
            top_k=top_k,
            modality=modality,
            reranker_fn=reranker_fn,
            source_meta_provider=lambda *a, **k: {},
            weights=cfg.weights,
        )

    return retrieve_fn


def build_llm(cfg: ExperimentConfig) -> tuple[Ollama, str, bool]:
    """Build the generation LLM from cfg. Returns (llm, resolved_chat_model, effective_thinking)."""
    chat_model = cfg.chat_model or get_setting("chat_model")
    host = get_setting("ollama_host")
    effective_thinking = bool(cfg.thinking) and llm_runtime.model_supports_thinking(chat_model)
    llm = Ollama(
        model=chat_model,
        base_url=host,
        request_timeout=6700.0,
        temperature=0.0,
        thinking=effective_thinking,
    )
    return llm, chat_model, effective_thinking


def apply_embed_override(cfg: ExperimentConfig) -> str:
    """If cfg overrides the embed model, set it on Settings (must match the ingested collection)."""
    embed_model = cfg.embed_model or get_setting("embed_model")
    if cfg.embed_model and cfg.embed_model != get_setting("embed_model"):
        Settings.embed_model = OllamaEmbedding(model_name=cfg.embed_model, base_url=get_setting("ollama_host"))
    return embed_model


# --------------------------------------------------------------------------- run dir

def _git_short_hash() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(_bootstrap.EVAL_ROOT), text=True
        ).strip()
    except Exception:
        return "nogit"


def _make_run_dir(cfg: ExperimentConfig, chat_model: str, embed_model: str, effective_thinking: bool) -> tuple[Path, dict]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    git_hash = _git_short_hash()
    # Uniquifier so two same-second launches never clobber each other.
    base = _bootstrap.RUNS_DIR / cfg.dataset / f"{stamp}_{git_hash}"
    run_dir = base
    n = 1
    while run_dir.exists():
        run_dir = Path(f"{base}_{n}")
        n += 1
    run_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "dataset": cfg.dataset,
        "timestamp": stamp,
        "git_hash": git_hash,
        "top_k": cfg.top_k,
        "reranker": cfg.reranker,
        "prompt": cfg.prompt,
        "thinking_enabled": effective_thinking,
        "questions": cfg.questions,
        "embed_model": embed_model,
        "chat_model": chat_model,
        "weights": {"relevance": cfg.weights.relevance, "temporal": cfg.weights.temporal},
    }
    return run_dir, config


# --------------------------------------------------------------------------- main

def run(cfg: ExperimentConfig) -> int:
    paths = _bootstrap.use_dataset(cfg.dataset)
    index_map_path = paths["index"]
    questions_path = paths["dir"] / cfg.questions
    if not index_map_path.exists():
        print(f"{index_map_path} not found. Run: python harness/ingest.py --dataset {cfg.dataset}", file=sys.stderr)
        return 1
    if not questions_path.exists():
        print(f"{questions_path} not found.", file=sys.stderr)
        return 1

    questions = json.loads(questions_path.read_text(encoding="utf-8"))["questions"]
    source_to_note = {int(k): v for k, v in json.loads(index_map_path.read_text(encoding="utf-8")).items()}

    # Wire the injected components (no monkeypatching).
    embed_model = apply_embed_override(cfg)
    llm, chat_model, effective_thinking = build_llm(cfg)
    prompt = get_prompt(cfg.prompt)
    retrieve_fn = build_retriever(cfg)

    run_dir, config = _make_run_dir(cfg, chat_model, embed_model, effective_thinking)
    print(f"Experiment: dataset={cfg.dataset} prompt={cfg.prompt} reranker={cfg.reranker} "
          f"chat_model={chat_model} thinking={effective_thinking} top_k={cfg.top_k}")

    rows: list[dict] = []
    for i, q in enumerate(questions, start=1):
        print(f"[{i:2d}/{len(questions)}] {q['id']}: {q['question'][:70]}...", flush=True)
        try:
            result = generation.query_sources(
                q["question"], top_k=cfg.top_k, prompt=prompt, llm=llm, retrieve_fn=retrieve_fn)
        except Exception as exc:
            print(f"    FAILED: {exc}", file=sys.stderr)
            result = {"answer": f"<ERROR: {exc}>", "sources": []}

        retrieved_note_ids, retrieved_scores, retrieved_texts = [], [], []
        for src in result.get("sources", []):
            sid = src.get("source_id")
            note_id = source_to_note.get(int(sid)) if sid is not None else None
            retrieved_note_ids.append(note_id or f"unknown-{sid}")
            retrieved_scores.append(round(float(src.get("score") or 0.0), 4))
            retrieved_texts.append((src.get("text") or "").strip())

        rows.append({
            "id": q["id"],
            "question": q["question"],
            "expected_answer": q["expected_answer"],
            "answerability": q["answerability"],
            "gold_supporting_notes": "|".join(q["gold_supporting_notes"]),
            "generated_answer": (result.get("answer") or "").strip(),
            "retrieved_note_ids": "|".join(retrieved_note_ids),
            "retrieved_scores": "|".join(str(s) for s in retrieved_scores),
            "retrieved_texts": "\n---\n".join(retrieved_texts),
        })

    raw_csv = run_dir / "raw.csv"
    raw_jsonl = run_dir / "raw.jsonl"
    with raw_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    with raw_jsonl.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    (run_dir / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    # Consistent evaluation output: retrieval + state-aware answer metrics.
    summary, counts, buckets = evaluation.evaluate(run_dir, questions_path, paths["world"], cfg.top_k)
    evaluation.print_summary(summary, counts, buckets, cfg.top_k)
    print(f"\nRun folder: {run_dir}")
    return 0


def _cfg_from_args(args) -> ExperimentConfig:
    if args.config:
        data = json.loads(Path(args.config).read_text(encoding="utf-8"))
        w = data.pop("weights", None)
        cfg = ExperimentConfig(**data)
        if w:
            cfg.weights = RankWeights(relevance=w.get("relevance", 1.0), temporal=w.get("temporal", 0.3))
        return cfg
    return ExperimentConfig(
        dataset=args.dataset,
        top_k=args.top_k,
        reranker=args.reranker,
        prompt=args.prompt,
        chat_model=args.chat_model,
        embed_model=args.embed_model,
        thinking=args.thinking,
        questions=args.questions,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=None, help="JSON file with an ExperimentConfig (overrides other flags)")
    parser.add_argument("--dataset", default="stateful",
                        help=f"dataset under datasets/ (have: {', '.join(_bootstrap.list_datasets()) or 'none'})")
    parser.add_argument("--top-k", dest="top_k", type=int, default=5)
    parser.add_argument("--prompt", default="default", help="prompt variant name (default, strict_refusal, ...)")
    parser.add_argument("--chat-model", dest="chat_model", default=None, help="override settings chat_model")
    parser.add_argument("--embed-model", dest="embed_model", default=None, help="override settings embed_model (must match ingest)")
    parser.add_argument("--questions", default="questions.json")
    rerank = parser.add_mutually_exclusive_group()
    rerank.add_argument("--reranker", dest="reranker", action="store_true", default=True)
    rerank.add_argument("--no-reranker", dest="reranker", action="store_false")
    think = parser.add_mutually_exclusive_group()
    think.add_argument("--thinking", dest="thinking", action="store_true", default=False)
    think.add_argument("--no-thinking", dest="thinking", action="store_false")
    args = parser.parse_args()
    return run(_cfg_from_args(args))


if __name__ == "__main__":
    sys.exit(main())
