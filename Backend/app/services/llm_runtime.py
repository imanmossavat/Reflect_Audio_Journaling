"""Ollama / LlamaIndex runtime plumbing shared by retrieval (embeddings) and
generation (the LLM).

Lives in its own module so `retrieval` and `generation` can both depend on it
without importing each other (avoids a retrieval↔generation cycle). Holds:
- settings accessors (`_ollama_base_url` / `_embed_model` / `_llm_model`),
- the dynamic module attributes shim (`OLLAMA_BASE_URL` / `EMBED_MODEL` / `LLM_MODEL`),
- Ollama health + capability checks,
- `configure_llamaindex()` which wires `Settings.embed_model` / `Settings.llm`.
"""
import shutil
from typing import Any

import httpx
from llama_index.core import Settings
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama

from app.services.settings_service import get_setting


def _ollama_base_url() -> str:
    return get_setting("ollama_host").rstrip("/")


def _embed_model() -> str:
    return get_setting("embed_model")


def _llm_model() -> str:
    return get_setting("chat_model")


# WARNING: `from app.services.llm_runtime import EMBED_MODEL` binds the value at import
# time and won't reflect later settings changes. Use module attribute access
# (`llm_runtime.EMBED_MODEL`) or call get_setting() directly where a fresh value is needed.
def __getattr__(name: str) -> Any:
    if name == "OLLAMA_BASE_URL":
        return _ollama_base_url()
    if name == "EMBED_MODEL":
        return _embed_model()
    if name == "LLM_MODEL":
        return _llm_model()
    raise AttributeError(f"module 'app.services.llm_runtime' has no attribute {name!r}")


def check_ollama_state() -> str:
    try:
        with httpx.Client(timeout=3.0) as client:
            client.get(_ollama_base_url())
        return "ok"
    except httpx.ConnectError:
        return "not_running" if shutil.which("ollama") else "not_installed"
    except Exception:
        return "not_running"


def check_model_installed(model: str) -> bool:
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{_ollama_base_url()}/api/tags")
            response.raise_for_status()
            installed = {m.get("name", "") for m in response.json().get("models", [])}
        return any(name == model or name.startswith(f"{model}:") for name in installed)
    except Exception:
        return True


_thinking_capability_cache: dict[tuple[str, str], bool] = {}


def model_supports_thinking(model: str) -> bool:
    # Returns True if Ollama reports the model has the 'thinking' capability.
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
    # Returns 'not_running', 'model_missing', or 'unknown' based on the exception.
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


def _thinking_enabled() -> bool:
    return bool(get_setting("thinking_enabled"))


_llamaindex_signature: tuple[str, str, str, bool, int] | None = None


def configure_llamaindex() -> None:
    global _llamaindex_signature
    embed = _embed_model()
    llm = _llm_model()
    host = _ollama_base_url()
    # Only think when the toggle is on AND the model actually supports it.
    thinking = _thinking_enabled() and model_supports_thinking(llm)
    # Shared context window — llama_index maps context_window -> num_ctx, so this keeps the
    # RAG/chat path on the same window as the direct Ollama calls (avoids model reloads).
    num_ctx = int(get_setting("num_ctx"))
    signature = (embed, llm, host, thinking, num_ctx)
    if _llamaindex_signature == signature:
        return
    Settings.embed_model = OllamaEmbedding(
        model_name=embed,
        base_url=host,
    )
    Settings.llm = Ollama(
        model=llm,
        base_url=host,
        request_timeout=6700.0,
        temperature=0.0,
        thinking=thinking,
        context_window=num_ctx,
    )
    _llamaindex_signature = signature


configure_llamaindex()
