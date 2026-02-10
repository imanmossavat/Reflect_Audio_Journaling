import subprocess
import time
import sys
import os

def get_python_executable(root_dir):
    """Finds the python executable, prioritizing Conda environments."""
    
    # Check if running in a Conda environment
    if "CONDA_PREFIX" in os.environ:
        print(f"[Info] Conda environment detected: {os.environ.get('CONDA_DEFAULT_ENV', 'unknown')}")
        print(f"[Info] Using Conda Python: {sys.executable}")
        return sys.executable
    
    # Fall back to local .venv or venv
    for venv_name in [".venv", "venv"]:
        if os.name == 'nt': # Windows
            python_path = os.path.join(root_dir, "Backend", venv_name, "Scripts", "python.exe")
        else: # Mac/Linux
            python_path = os.path.join(root_dir, "Backend", venv_name, "bin", "python")

        if os.path.exists(python_path):
            print(f"[Info] Using virtual environment Python: {python_path}")
            return python_path
    
    print(f"[Warning] No virtual environment found, using system Python: {sys.executable}")
    return sys.executable

def run_system():
    # 1. Path Logic
    app_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(app_dir)
    root_dir = os.path.dirname(backend_dir)
    frontend_dir = os.path.join(root_dir, "Frontend")

    python_exe = get_python_executable(root_dir)

    # 2. Environment Setup (The fix for "No module named app")
    # We add the Backend directory to the Python Path
    env = os.environ.copy()
    env["PYTHONPATH"] = backend_dir + os.pathsep + env.get("PYTHONPATH", "")

    # 3. Start Frontend
    print(f"[Supervisor] Starting Frontend...")
    try:
        frontend_proc = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=frontend_dir,
            shell=os.name == 'nt'
        )
    except Exception as e:
        print(f"[Error] Could not start frontend: {e}")
        frontend_proc = None

    # 4. Start Backend Loop
    try:
        while True:
            print(f"\n[Supervisor] Starting Backend Engine (main.py)...")

            # We run the process using the backend_dir as the base 
            # so that 'import app' works correctly.
            backend_proc = subprocess.run(
                [python_exe, "app/main.py"],
                cwd=backend_dir,
                env=env
            )

            print(f"\n[Supervisor] Backend exited (Code {backend_proc.returncode})")
            print("[Supervisor] Restarting Backend in 2s...")
            time.sleep(2)

    except KeyboardInterrupt:
        print("\n[Supervisor] Shutting down system...")
        if frontend_proc:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(frontend_proc.pid)])
            else:
                frontend_proc.terminate()
        sys.exit(0)

if __name__ == "__main__":
    run_system()