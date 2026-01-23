import os
import json
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from app.core.config import settings
from app.core.system_check import get_system_info, install_cuda_torch

router = APIRouter()

class SetupConfig(BaseModel):
    data_dir: str
    config_dir: str
    language: str
    whisper_model: str
    device: str

@router.get("/status")
async def get_setup_status():
    return {
        "is_configured": settings.IS_CONFIGURED,
        "system_info": get_system_info(),
        "current_config": {
            "data_dir": settings.DATA_DIR,
            "config_dir": settings.CONFIG_DIR,
            "language": settings.LANGUAGE,
            "whisper_model": settings.WHISPER_MODEL,
            "device": settings.DEVICE
        }
    }

@router.post("/run")
async def run_setup(config: SetupConfig, background_tasks: BackgroundTasks):
    try:
        # Create directories if they don't exist
        os.makedirs(config.data_dir, exist_ok=True)
        os.makedirs(config.config_dir, exist_ok=True)
        
        # Save to frontend_settings.json
        settings_path = os.path.join(config.config_dir, "frontend_settings.json")
        settings_data = {
            "DATA_DIR": config.data_dir,
            "CONFIG_DIR": config.config_dir,
            "LANGUAGE": config.language,
            "WHISPER_MODEL": config.whisper_model,
            "DEVICE": config.device
        }
        
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings_data, f, indent=4)
            
        # Update current settings
        settings.DATA_DIR = config.data_dir
        settings.CONFIG_DIR = config.config_dir
        settings.LANGUAGE = config.language
        settings.WHISPER_MODEL = config.whisper_model
        settings.DEVICE = config.device
        settings.IS_CONFIGURED = True
        
        # If user chose CUDA but it's not available, try to install it in background
        system_info = get_system_info()
        if config.device == "cuda" and not system_info["cuda_available"]:
            background_tasks.add_task(install_cuda_torch)
            return {"message": "Setup saved. CUDA installation started in background. The engine might restart or require a manual restart later.", "status": "installing"}

        return {"message": "Setup successful", "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
