import pytest
import os
import json
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_setup_deps():
    with patch("app.api.setup_routes.get_system_info") as mock_info, \
         patch("app.api.setup_routes.install_cuda_torch") as mock_install:
        mock_info.return_value = {"cuda_available": False, "device": "cpu"}
        yield mock_info, mock_install

def test_get_setup_status(client, mock_setup_deps):
    response = client.get("/api/setup/status")
    assert response.status_code == 200
    assert "is_configured" in response.json()
    assert "system_info" in response.json()

def test_run_setup(client, mock_setup_deps, test_setup):
    # test_setup fixture provides temp data/config dirs
    from app.core.config import settings
    
    payload = {
        "data_dir": settings.DATA_DIR,
        "config_dir": settings.CONFIG_DIR,
        "language": "nl",
        "whisper_model": "base",
        "device": "cpu"
    }
    
    response = client.post("/api/setup/run", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # Check if settings file was created
    settings_path = os.path.join(settings.CONFIG_DIR, "frontend_settings.json")
    assert os.path.exists(settings_path)
    with open(settings_path, "r") as f:
        saved = json.load(f)
    assert saved["LANGUAGE"] == "nl"
    assert settings.LANGUAGE == "nl"
