import subprocess
import os
import sys
import shutil

def run_command(command, cwd=None, shell=True):
    print(f"\n[Setup] Running: {' '.join(command) if isinstance(command, list) else command}")
    try:
        process = subprocess.run(
            command,
            cwd=cwd,
            shell=shell,
            check=True,
            text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"[Error] Command failed with exit code {e.returncode}")
        return False

def setup():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(root_dir, "Backend")
    frontend_dir = os.path.join(root_dir, "Frontend")

    print("🚀 Starting REFLECT Project Setup...")

    # 1. Setup Backend
    print("\n--- 🧠 Setting up Backend ---")
    if not os.path.exists(backend_dir):
        print("[Error] Backend directory not found!")
        return

    # Create Virtual Environment
    venv_dir = os.path.join(backend_dir, ".venv")
    
    # Check if venv exists but is broken (missing pyvenv.cfg)
    if os.path.exists(venv_dir) and not os.path.exists(os.path.join(venv_dir, "pyvenv.cfg")):
        print("[Setup] Broken virtual environment detected (missing pyvenv.cfg). Deleting...")
        shutil.rmtree(venv_dir)

    if not os.path.exists(venv_dir):
        print("[Setup] Creating virtual environment with Python 3.10...")
        if os.name == 'nt':
            # Use 'py -3.10' launcher on Windows as requested
            success = run_command(["py", "-3.10", "-m", "venv", ".venv"], cwd=backend_dir)
            if not success:
                print("[Warning] 'py -3.10' failed. Falling back to default python...")
                run_command([sys.executable, "-m", "venv", ".venv"], cwd=backend_dir)
        else:
            run_command([sys.executable, "-m", "venv", ".venv"], cwd=backend_dir)
    else:
        print("[Setup] Virtual environment already exists.")

    # Install Requirements
    python_exe = os.path.join(venv_dir, "Scripts", "python.exe") if os.name == 'nt' else os.path.join(venv_dir, "bin", "python")
    
    if os.path.exists(python_exe):
        print(f"[Setup] Using python at: {python_exe}")
        # Ensure pip is installed
        run_command([python_exe, "-m", "ensurepip", "--upgrade"], cwd=backend_dir)
        # Upgrade pip and install requirements
        run_command([python_exe, "-m", "pip", "install", "--upgrade", "pip"], cwd=backend_dir)
        run_command([python_exe, "-m", "pip", "install", "-r", "requirements.txt"], cwd=backend_dir)
    else:
        print("[Error] Could not find python executable in virtual environment. Consider deleting the .venv folder and running setup again.")

    # 2. Setup Frontend
    print("\n--- 💻 Setting up Frontend ---")
    if not os.path.exists(frontend_dir):
        print("[Error] Frontend directory not found!")
    else:
        # Try to use npm (standard)
        print("[Setup] Installing frontend dependencies (this may take a minute)...")
        run_command(["npm", "install"], cwd=frontend_dir)

    print("\n✅ Setup Complete!")
    print("\nTo start the project:")
    print("1. Click 'start_engine.bat' (Windows) or 'start_engine.command' (Mac)")
    print("2. The browser will open automatically at http://localhost:3000")

if __name__ == "__main__":
    setup()
