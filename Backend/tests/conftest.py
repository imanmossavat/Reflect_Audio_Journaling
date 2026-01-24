import pytest
import os
import shutil
import tempfile
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

@pytest.fixture(scope="function", autouse=True)
def test_setup():
    """Setup temporary directories for testing."""
    # Create temp dirs
    temp_base = tempfile.mkdtemp()
    temp_data = os.path.join(temp_base, "data")
    temp_config = os.path.join(temp_base, "configs")
    os.makedirs(temp_data, exist_ok=True)
    os.makedirs(temp_config, exist_ok=True)
    
    # Backup original settings
    orig_data_dir = settings.DATA_DIR
    orig_config_dir = settings.CONFIG_DIR
    
    # Override settings for tests
    settings.DATA_DIR = temp_data
    settings.CONFIG_DIR = temp_config
    
    yield
    
    # Cleanup
    shutil.rmtree(temp_base)
    
    # Restore (optional, but good practice if session scope)
    settings.DATA_DIR = orig_data_dir
    settings.CONFIG_DIR = orig_config_dir

@pytest.fixture
def client():
    """FastAPI test client."""
    with TestClient(app) as c:
        yield c
