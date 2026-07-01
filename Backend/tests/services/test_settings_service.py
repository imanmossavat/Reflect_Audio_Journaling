"""Coverage for the device-availability guard added after a stale settings.json
(device: cuda) survived a torch reinstall and crashed transcription on a
colleague's Windows machine — see CHANGES.md, July 2026."""

import sys

import pytest

from app.services import settings_service


# ---------------------------------------------------------------------------
# device_available()
# ---------------------------------------------------------------------------

def test_cpu_is_always_available():
    assert settings_service.device_available("cpu") is True


def test_cuda_available_when_torch_reports_it(monkeypatch):
    import torch
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    assert settings_service.device_available("cuda") is True


def test_cuda_unavailable_when_torch_reports_it(monkeypatch):
    import torch
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert settings_service.device_available("cuda") is False


def test_mps_available_when_torch_reports_it(monkeypatch):
    import torch
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: True)
    assert settings_service.device_available("mps") is True


def test_mps_unavailable_when_torch_reports_it(monkeypatch):
    import torch
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: False)
    assert settings_service.device_available("mps") is False


def test_rocm_requires_hip_build_and_cuda_available(monkeypatch):
    import torch
    monkeypatch.setattr(torch.version, "hip", "6.0", raising=False)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    assert settings_service.device_available("rocm") is True


def test_rocm_unavailable_without_hip_build(monkeypatch):
    import torch
    monkeypatch.setattr(torch.version, "hip", None, raising=False)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    assert settings_service.device_available("rocm") is False


def test_unknown_device_id_is_unavailable():
    assert settings_service.device_available("tpu") is False


def test_device_unavailable_when_torch_not_importable(monkeypatch):
    # `import torch` inside device_available raises ImportError when the
    # module is present in sys.modules as None -- the standard way to
    # simulate a missing import without uninstalling the real package.
    monkeypatch.setitem(sys.modules, "torch", None)
    assert settings_service.device_available("cuda") is False


# ---------------------------------------------------------------------------
# _validate() rejecting a device that isn't actually usable
# ---------------------------------------------------------------------------

def test_validate_rejects_unavailable_device(monkeypatch):
    monkeypatch.setattr(settings_service, "device_available", lambda device: False)
    with pytest.raises(ValueError, match="not available"):
        settings_service._validate({"device": "cuda"})


def test_validate_accepts_available_device(monkeypatch):
    monkeypatch.setattr(settings_service, "device_available", lambda device: True)
    cleaned = settings_service._validate({"device": "cuda"})
    assert cleaned == {"device": "cuda"}


def test_validate_still_rejects_unknown_device_id():
    with pytest.raises(ValueError, match="must be one of"):
        settings_service._validate({"device": "tpu"})
