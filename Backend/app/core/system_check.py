import torch
import platform
import subprocess
import sys
import os

def get_system_info():
    info = {
        "os": platform.system(),
        "arch": platform.machine(),
        "python_version": sys.version,
        "cuda_available": torch.cuda.is_available(),
        "mps_available": False,
        "suggested_device": "cpu"
    }
    
    if hasattr(torch.backends, "mps"):
        info["mps_available"] = torch.backends.mps.is_available()
    
    if info["cuda_available"]:
        info["suggested_device"] = "cuda"
        info["cuda_device_name"] = torch.cuda.get_device_name(0)
    elif info["mps_available"]:
        info["suggested_device"] = "mps"
    
    return info

def install_cuda_torch():
    """Attempts to install CUDA-enabled torch for Windows/Linux."""
    print("Installing CUDA-enabled PyTorch...")
    pip_cmd = [sys.executable, "-m", "pip", "install", "torch", "torchaudio", "--index-url", "https://download.pytorch.org/whl/cu124", "--force-reinstall"]
    try:
        subprocess.check_call(pip_cmd)
        return True
    except Exception as e:
        print(f"Failed to install CUDA torch: {e}")
        return False
