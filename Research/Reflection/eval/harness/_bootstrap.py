"""Import this FIRST in every harness script.

The facilitator eval is pure prompt -> LLM (no retrieval, no Chroma), so unlike the
RAG harness this only needs ONE thing: put Backend/ on sys.path so
`from app.prompts import gibbs_facilitator_prompt` and
`from app.services.settings_service import get_setting, chat_num_ctx` resolve.

It deliberately does NOT touch app.services.chroma / torch / the vector store — the
facilitator never retrieves, so there is nothing to isolate.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent        # eval/harness
EVAL_ROOT = HERE.parent                        # eval
REPO_ROOT = HERE.parents[3]                     # harness -> eval -> Reflection -> Research -> repo
BACKEND_DIR = REPO_ROOT / "Backend"
DATASETS_DIR = EVAL_ROOT / "datasets"
RUNS_DIR = EVAL_ROOT / "runs"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def dataset_paths(name: str) -> dict:
    """Canonical file locations for a dataset (no side effects)."""
    d = DATASETS_DIR / name
    return {"name": name, "dir": d, "cases": d / "cases.json"}


def list_datasets() -> list[str]:
    if not DATASETS_DIR.exists():
        return []
    return sorted(p.name for p in DATASETS_DIR.iterdir() if p.is_dir())
