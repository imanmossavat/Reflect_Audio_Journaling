"""Import this FIRST in every eval script.

Adds Backend/ to sys.path so `from app.services.rag import ...` works, and
monkey-patches the Chroma module to use an isolated DB inside maya_eval/
so eval embeddings never land in Backend/database/chroma/.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent.parent
BACKEND_DIR = REPO_ROOT / "Backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

EVAL_CHROMA_PATH = HERE / "chroma"
EVAL_CHROMA_PATH.mkdir(parents=True, exist_ok=True)
EVAL_COLLECTION_NAME = "maya_eval_chunks"

from app.services import chroma as _chroma  # noqa: E402

_chroma.CHROMA_PATH = EVAL_CHROMA_PATH
_chroma.COLLECTION_NAME = EVAL_COLLECTION_NAME
_chroma._client = None
_chroma._collection = None


def reset_chroma_collection() -> None:
    """Drop and recreate the eval collection. Idempotent."""
    import chromadb

    client = chromadb.PersistentClient(path=str(EVAL_CHROMA_PATH))
    try:
        client.delete_collection(EVAL_COLLECTION_NAME)
    except Exception:
        pass
    _chroma._client = None
    _chroma._collection = None
