"""Import this FIRST in every harness script (and in the dataset generators).

- Adds Backend/ to sys.path so `from app.services... import ...` works.
- Points the Chroma module at an isolated, PER-DATASET DB inside eval/chroma/<dataset>/
  so eval embeddings never touch Backend/database/chroma/ AND the datasets
  (baseline / stateful) never share a collection.

Call use_dataset(name) before indexing or querying so the right collection is active.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent       # eval/harness
EVAL_ROOT = HERE.parent                       # eval
REPO_ROOT = HERE.parents[3]                    # repo root  (harness -> eval -> RAG -> Research -> repo)
BACKEND_DIR = REPO_ROOT / "Backend"
DATASETS_DIR = EVAL_ROOT / "datasets"
RUNS_DIR = EVAL_ROOT / "runs"
CHROMA_BASE = EVAL_ROOT / "chroma"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Load torch BEFORE chromadb. chromadb bundles onnxruntime, whose native runtime
# conflicts with torch's when torch is imported second -> hard segfault (exit 139,
# no Python traceback) the moment the BGE reranker imports sentence_transformers
# mid-eval. Importing torch here, ahead of `app.services.chroma`, orders it correctly.
try:
    import torch  # noqa: F401
except ImportError:
    pass

from app.services import chroma as _chroma  # noqa: E402

_active_dataset: str | None = None


def dataset_paths(name: str) -> dict:
    """Canonical file locations for a dataset (no side effects)."""
    d = DATASETS_DIR / name
    return {
        "name": name,
        "dir": d,
        "world": d / "world_state.json",
        "notes": d / "notes.json",
        "index": d / "notes_index.json",
        "questions": d / "questions.json",
    }


def use_dataset(name: str) -> dict:
    """Activate dataset `name`: isolate its Chroma collection, return its paths."""
    global _active_dataset
    path = CHROMA_BASE / name
    path.mkdir(parents=True, exist_ok=True)
    _chroma.CHROMA_PATH = path
    _chroma.COLLECTION_NAME = f"{name}_chunks"
    _chroma._client = None
    _chroma._collection = None
    _active_dataset = name
    return dataset_paths(name)


def reset_chroma_collection() -> None:
    """Drop and recreate the ACTIVE dataset's collection. Call use_dataset() first."""
    import chromadb

    if _active_dataset is None:
        raise RuntimeError("call use_dataset(name) before reset_chroma_collection()")
    client = chromadb.PersistentClient(path=str(_chroma.CHROMA_PATH))
    try:
        client.delete_collection(_chroma.COLLECTION_NAME)
    except Exception:
        pass
    _chroma._client = None
    _chroma._collection = None


def list_datasets() -> list[str]:
    if not DATASETS_DIR.exists():
        return []
    return sorted(p.name for p in DATASETS_DIR.iterdir() if p.is_dir())
