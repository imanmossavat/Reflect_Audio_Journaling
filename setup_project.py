import subprocess
import os
import sys
import shutil

# -----------------------------
# Config
# -----------------------------
VERBOSE = True  # Set to False to reduce output

def vprint(*args):
    if VERBOSE:
        print(*args)

# -----------------------------
# Helper function
# -----------------------------
def run_command(command, cwd=None, shell=True):
    vprint(f"\n[Setup] Running command: {' '.join(command) if isinstance(command, list) else command}")
    try:
        # If command is a list, always use shell=False
        if isinstance(command, list):
            subprocess.run(command, cwd=cwd, check=True, text=True, shell=False)
        else:
            subprocess.run(command, cwd=cwd, check=True, text=True, shell=shell)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[Error] Command failed with exit code {e.returncode}")
        return False

def get_command_output(command):
    """Run a command and safely capture output without interactive REPL"""
    return subprocess.getoutput(command)

# -----------------------------
# Setup function
# -----------------------------
def setup():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(root_dir, "Backend")
    frontend_dir = os.path.join(root_dir, "Frontend")

    vprint("🚀 Starting REFLECT Project Setup...")
    vprint(f"[Info] Project root directory: {root_dir}")

    # Detect Conda
    is_conda = "CONDA_PREFIX" in os.environ
    vprint(f"[Info] Conda detected: {is_conda}")
    if is_conda:
        vprint(f"[Info] Conda prefix: {os.environ['CONDA_PREFIX']}")
    vprint(f"[Info] Python executable before setup: {sys.executable}")
    python_version_safe = get_command_output(f'"{sys.executable}" --version')
    vprint(f"[Info] Python version: {python_version_safe}")

    # -----------------------------
    # Backend setup
    # -----------------------------
    print("\n--- 🧠 Setting up Backend ---")
    if not os.path.exists(backend_dir):
        print("[Error] Backend directory not found!")
        return

    venv_dir = os.path.join(backend_dir, ".venv")

    if is_conda:
        print("[Setup] Conda environment detected. Skipping .venv creation.")
        python_exe = sys.executable
    else:
        # Check for broken venv
        if os.path.exists(venv_dir) and not os.path.exists(os.path.join(venv_dir, "pyvenv.cfg")):
            print("[Setup] Broken virtual environment detected. Deleting...")
            shutil.rmtree(venv_dir)

        # Create venv if it doesn't exist
        if not os.path.exists(venv_dir):
            print("[Setup] Creating virtual environment (.venv) with Python 3.10+...")
            run_command([sys.executable, "-m", "venv", ".venv"], cwd=backend_dir)
        else:
            print("[Setup] Virtual environment already exists.")

        python_exe = os.path.join(venv_dir, "Scripts", "python.exe") if os.name == 'nt' else os.path.join(venv_dir, "bin", "python")

    # Safe Python & pip info
    vprint(f"[Info] Using Python executable: {python_exe}")
    python_version_safe = get_command_output(f'"{python_exe}" --version')
    vprint(f"[Info] Python version: {python_version_safe}")
    pip_version_safe = get_command_output(f'"{python_exe}" -m pip --version')
    vprint(f"[Info] Pip version: {pip_version_safe}")

    # Upgrade pip (safe for both Conda and venv)
    print("[Setup] Upgrading pip to the latest version...")
    run_command([python_exe, "-m", "pip", "install", "--upgrade", "pip"], cwd=backend_dir)

    # Install backend requirements
    requirements_file = os.path.join(backend_dir, "requirements.txt")
    if os.path.exists(requirements_file):
        print("[Setup] Installing backend requirements from requirements.txt...")
        run_command([python_exe, "-m", "pip", "install", "-r", requirements_file], cwd=backend_dir)
    else:
        print("[Warning] requirements.txt not found in Backend folder.")

    # -----------------------------
    # Frontend setup
    # -----------------------------
    print("\n--- 💻 Setting up Frontend ---")
    if not os.path.exists(frontend_dir):
        print("[Error] Frontend directory not found!")
    else:
        print("[Setup] Installing frontend dependencies (npm install)...")
        run_command(["npm", "install"], cwd=frontend_dir)

    # -----------------------------
    # Finish
    # -----------------------------
    print("\n✅ Setup Complete!")
    print(f"[Info] Python being used: {python_exe}")
    python_version_safe = get_command_output(f'"{python_exe}" --version')
    print(f"[Info] Python version: {python_version_safe}")
    pip_version_safe = get_command_output(f'"{python_exe}" -m pip --version')
    print(f"[Info] Pip version: {pip_version_safe}")
    print("[Info] Conda environment active:", os.environ.get("CONDA_DEFAULT_ENV", "None"))
    print("\nTo start the project:")
    print("1. Click 'start_engine.bat' (Windows) or 'start_engine.command' (Mac)")
    print("2. The browser will open automatically at http://localhost:3000\n")

if __name__ == "__main__":
    setup()
