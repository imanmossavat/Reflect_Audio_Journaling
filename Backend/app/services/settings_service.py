import json
import os
import threading
from pathlib import Path
from typing import Any

from app.logging_config import logger


_BACKEND_DIR = Path(__file__).resolve().parents[2]
_SETTINGS_PATH = _BACKEND_DIR / "data" / "settings.json"

DEFAULTS: dict[str, Any] = {
    "chat_model": "gemma4:e4b",
    "embed_model": "nomic-embed-text",
    "ollama_host": "http://localhost:11434",
    "device": "cpu",
    "whisper_model": "base",
    "language": "en",
    "db_path": str((_BACKEND_DIR / "database" / "database.db").as_posix()),
    "theme": "system",
    "date_format": "dmy",
}

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


def _validate(patch: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in patch.items():
        if key not in DEFAULTS:
            continue
        if key == "device":
            if value not in ALLOWED_DEVICES:
                raise ValueError(f"device must be one of {sorted(ALLOWED_DEVICES)}")
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
