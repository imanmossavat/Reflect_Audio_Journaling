"""Coverage for TranscriptionManager's device fallback -- the actual fix for
the crash a colleague hit on Windows (stale device=cuda + CPU-only torch ->
AssertionError deep inside WhisperX/pyannote). See CHANGES.md, July 2026.

WhisperX/torch model loading is too heavy for a unit test, so _load_whisperx
and the model-loading calls are stubbed; only the device-selection logic in
__init__ is under test.
"""

import types

import pytest

from app.services import transcription as transcription_module
from app.services.transcription import TranscriptionManager


def _fake_get_setting(overrides):
    def _get(key):
        return overrides[key]
    return _get


@pytest.fixture
def stub_whisperx(monkeypatch):
    fake_whisperx = types.SimpleNamespace(
        load_model=lambda *a, **k: object(),
        load_align_model=lambda **k: (object(), {"language": "en"}),
    )
    monkeypatch.setattr(TranscriptionManager, "_load_whisperx", staticmethod(lambda: fake_whisperx))
    return fake_whisperx


def _patch_settings(monkeypatch, device):
    monkeypatch.setattr(
        "app.config.get_setting",
        _fake_get_setting({"device": device, "whisper_model": "base", "language": "en"}),
    )


def test_falls_back_to_cpu_when_configured_device_unavailable(monkeypatch, stub_whisperx):
    _patch_settings(monkeypatch, "cuda")
    monkeypatch.setattr(transcription_module, "device_available", lambda device: False)

    manager = TranscriptionManager()

    assert manager.device == "cpu"
    assert manager.compute_type == "int8"


def test_keeps_configured_device_when_available(monkeypatch, stub_whisperx):
    _patch_settings(monkeypatch, "cuda")
    monkeypatch.setattr(transcription_module, "device_available", lambda device: True)

    manager = TranscriptionManager()

    assert manager.device == "cuda"
    assert manager.compute_type == "float16"


def test_cpu_configured_never_needs_fallback(monkeypatch, stub_whisperx):
    _patch_settings(monkeypatch, "cpu")
    calls = []
    monkeypatch.setattr(
        transcription_module, "device_available",
        lambda device: calls.append(device) or True,
    )

    manager = TranscriptionManager()

    assert manager.device == "cpu"
    assert calls == ["cpu"]
