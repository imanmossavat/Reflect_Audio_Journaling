import pytest
import os
import json
from unittest.mock import patch, MagicMock
from app.services.settings import SettingsManager
from app.core.config import settings

@pytest.fixture
def settings_manager():
    return SettingsManager()

def test_get_effective_settings_default(settings_manager):
    # Ensure no frontend_settings.json exists (test_setup clears it)
    eff = settings_manager.get_effective_settings()
    assert eff["LANGUAGE"] == settings.LANGUAGE
    assert eff["IS_CONFIGURED"] == settings.IS_CONFIGURED

def test_update_settings(settings_manager):
    new_payload = {"LANGUAGE": "nl", "WHISPER_MODEL": "large"}
    res = settings_manager.update_settings(new_payload)
    
    assert res["status"] == "ok"
    assert os.path.exists(settings_manager.frontend_path)
    
    with open(settings_manager.frontend_path, "r") as f:
        saved = json.load(f)
    assert saved["LANGUAGE"] == "nl"
    assert saved["WHISPER_MODEL"] == "large"

def test_reset_settings(settings_manager):
    # First create some settings
    settings_manager.update_settings({"test": "data"})
    assert os.path.exists(settings_manager.frontend_path)
    
    success = settings_manager.reset_settings()
    assert success is True
    assert not os.path.exists(settings_manager.frontend_path)

def test_open_folder(settings_manager):
    with patch("os.path.exists") as mock_exists, \
         patch("platform.system") as mock_sys, \
         patch("os.startfile") as mock_startfile:
        
        mock_exists.return_value = True
        mock_sys.return_value = "Windows"
        
        success, err = settings_manager.open_folder("C:/some/path")
        assert success is True
        mock_startfile.assert_called_once_with("C:/some/path")
