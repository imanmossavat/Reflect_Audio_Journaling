from typing import Any

import httpx
from fastapi import APIRouter, HTTPException

from app import logging_config
from app.services import settings_service

router = APIRouter(prefix="/settings", tags=["Settings"])

logger = logging_config.logger


@router.get("")
async def read_settings() -> dict[str, Any]:
    return settings_service.get_settings()


@router.put("")
async def write_settings(patch: dict[str, Any]) -> dict[str, Any]:
    try:
        return settings_service.update_settings(patch)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/devices")
async def list_devices() -> list[dict[str, Any]]:
    devices: list[dict[str, Any]] = [
        {"id": "cpu", "label": "CPU", "available": True, "detail": None, "supported_for_transcription": True},
    ]

    cuda_available = False
    cuda_detail: str | None = None
    mps_available = False
    rocm_available = False
    rocm_detail: str | None = None

    try:
        import torch  # type: ignore

        try:
            cuda_available = bool(torch.cuda.is_available())
        except Exception:
            cuda_available = False
        if cuda_available:
            try:
                cuda_detail = torch.cuda.get_device_name(0)
            except Exception:
                cuda_detail = None

        try:
            mps_available = bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available())
        except Exception:
            mps_available = False

        try:
            hip = getattr(torch.version, "hip", None)
            if hip and cuda_available:
                rocm_available = True
                rocm_detail = f"ROCm/HIP {hip}"
        except Exception:
            rocm_available = False
    except Exception:
        logger.info("torch not installed; only CPU device will be available")

    devices.append({
        "id": "cuda",
        "label": "CUDA (NVIDIA GPU)",
        "available": cuda_available and not rocm_available,
        "detail": cuda_detail,
        "supported_for_transcription": True,
    })
    devices.append({
        "id": "mps",
        "label": "MPS (Apple Silicon)",
        "available": mps_available,
        "detail": "Uses openai-whisper (PyTorch) — model downloads to ~/.cache/whisper/ on first use",
        "supported_for_transcription": True,
    })
    devices.append({
        "id": "rocm",
        "label": "ROCm (AMD GPU)",
        "available": rocm_available,
        "detail": rocm_detail,
        "supported_for_transcription": False,
    })

    return devices


@router.get("/ollama-models")
async def list_ollama_models() -> dict[str, Any]:
    host = settings_service.get_setting("ollama_host").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{host}/api/tags")
            response.raise_for_status()
            data = response.json()
        models = [
            {"name": m.get("name", ""), "size": m.get("size")}
            for m in data.get("models", [])
            if m.get("name")
        ]
        return {"available": True, "host": host, "models": models}
    except Exception as exc:
        logger.info(f"Ollama unreachable at {host}: {exc}")
        return {"available": False, "host": host, "models": [], "error": str(exc)}


@router.get("/spacy-models")
async def list_spacy_models() -> list[dict[str, Any]]:
    entries = [
        {"language": "en", "model": "en_core_web_sm"},
        {"language": "nl", "model": "nl_core_news_sm"},
    ]
    try:
        import spacy  # type: ignore

        for entry in entries:
            entry["installed"] = bool(spacy.util.is_package(entry["model"]))
    except Exception:
        for entry in entries:
            entry["installed"] = False
    return entries
