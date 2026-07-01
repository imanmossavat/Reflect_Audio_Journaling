import json
import os
import threading
from pathlib import Path
from typing import Any

from app.logging_config import logger


_BACKEND_DIR = Path(__file__).resolve().parents[2]
_SETTINGS_PATH = _BACKEND_DIR / "data" / "settings.json"


def _auto_detect_device() -> str:
    """Return the best available compute device: cuda > mps > cpu."""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
    except Exception:
        pass
    return "cpu"


def device_available(device: str) -> bool:
    """Check whether a device id is actually usable on this machine right now.

    Distinct from the DEFAULTS-time auto-detect: this re-checks against the
    current torch install, so a stale settings.json (e.g. copied from another
    machine, or written before a venv was reinstalled with a CPU-only torch
    build) doesn't silently claim an unusable device.
    """
    if device == "cpu":
        return True
    try:
        import torch
    except Exception:
        return False
    if device == "cuda":
        try:
            return bool(torch.cuda.is_available())
        except Exception:
            return False
    if device == "mps":
        try:
            return bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available())
        except Exception:
            return False
    if device == "rocm":
        try:
            hip = getattr(torch.version, "hip", None)
            return bool(hip and torch.cuda.is_available())
        except Exception:
            return False
    return False


DEFAULTS: dict[str, Any] = {
    "chat_model": "gemma4:e4b",
    # Shared context window for every chat_model call
    # ~45-min transcript (~8k tokens in) + worst-case output (~4k) + prompt/buffer.
    "num_ctx": 16384,
    "embed_model": "nomic-embed-text",
    "ollama_host": "http://localhost:11434",
    "device": _auto_detect_device(),
    "whisper_model": "base",
    "language": "en",
    "db_path": str((_BACKEND_DIR / "database" / "database.db").as_posix()),
    "theme": "system",
    "date_format": "dmy",
    "thinking_enabled": True,
    "safety_model": "llama-guard3:1b",
}

# safety guard is mandatory, can only be Llama Guard model for now
SAFETY_MODEL_BASE = "llama-guard3"

ALLOWED_DEVICES = {"cpu", "cuda", "mps", "rocm"}
ALLOWED_WHISPER_MODELS = {"tiny", "base", "small", "medium", "large-v3"}
ALLOWED_LANGUAGES = {"en", "nl"}
ALLOWED_THEMES = {"light", "dark", "system"}
ALLOWED_DATE_FORMATS = {"dmy", "mdy"}

_lock = threading.Lock()
_version = 0
_listeners: list = []


def _read_file() -> dict[str, Any]:
    if not _SETTINGS_PATH.exists():
        return {}
    try:
        with _SETTINGS_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        logger.warning(f"settings.json unreadable, using defaults: {exc}")
        return {}


def _write_file(data: dict[str, Any]) -> None:
    _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _SETTINGS_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _SETTINGS_PATH)


def get_settings() -> dict[str, Any]:
    with _lock:
        stored = _read_file()
        merged = {**DEFAULTS, **{k: v for k, v in stored.items() if k in DEFAULTS}}
        return merged


def get_setting(key: str) -> Any:
    return get_settings().get(key, DEFAULTS.get(key))


def chat_num_ctx() -> int:
    """Context window that EVERY call to ``chat_model`` must pass."""
    return int(get_setting("num_ctx"))


def _validate(patch: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in patch.items():
        if key not in DEFAULTS:
            continue
        if key == "device":
            if value not in ALLOWED_DEVICES:
                raise ValueError(f"device must be one of {sorted(ALLOWED_DEVICES)}")
            if not device_available(value):
                raise ValueError(f"device '{value}' is not available on this machine")
        elif key == "whisper_model":
            if value not in ALLOWED_WHISPER_MODELS:
                raise ValueError(f"whisper_model must be one of {sorted(ALLOWED_WHISPER_MODELS)}")
        elif key == "language":
            if value not in ALLOWED_LANGUAGES:
                raise ValueError(f"language must be one of {sorted(ALLOWED_LANGUAGES)}")
        elif key == "theme":
            if value not in ALLOWED_THEMES:
                raise ValueError(f"theme must be one of {sorted(ALLOWED_THEMES)}")
        elif key == "date_format":
            if value not in ALLOWED_DATE_FORMATS:
                raise ValueError(f"date_format must be one of {sorted(ALLOWED_DATE_FORMATS)}")
        elif key == "thinking_enabled":
            if not isinstance(value, bool):
                raise ValueError(f"{key} must be a boolean")
        elif key == "num_ctx":
            # bool is a subclass of int, so reject it explicitly.
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError("num_ctx must be a positive integer")
        elif key == "safety_model":
            if not isinstance(value, str) or not value.strip():
                raise ValueError("safety_model must be a non-empty string")
            value = value.strip()
            if value != SAFETY_MODEL_BASE and not value.startswith(f"{SAFETY_MODEL_BASE}:"):
                raise ValueError(
                    f"safety_model must be a Llama Guard model "
                    f"({SAFETY_MODEL_BASE} or {SAFETY_MODEL_BASE}:<tag>)"
                )
        elif key in ("chat_model", "embed_model", "ollama_host", "db_path"):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{key} must be a non-empty string")
            value = value.strip()
        cleaned[key] = value
    return cleaned


def update_settings(patch: dict[str, Any]) -> dict[str, Any]:
    global _version
    cleaned = _validate(patch)
    with _lock:
        current = _read_file()
        merged = {**DEFAULTS, **{k: v for k, v in current.items() if k in DEFAULTS}, **cleaned}
        _write_file(merged)
        _version += 1
        listeners = list(_listeners)
    for listener in listeners:
        try:
            listener(cleaned)
        except Exception:
            logger.exception("settings listener failed")
    return merged


def version() -> int:
    return _version


def on_change(listener) -> None:
    _listeners.append(listener)
