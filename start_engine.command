#!/bin/bash
# -----------------------------------------
# REFLECT Quick Start (Mac/Linux)
# Fully Conda-aware
# Backend runs in background, frontend and browser start safely
# -----------------------------------------


pkill -f "Reflect_Audio_Journaling/Backend/app/dev.py"
pkill -f "Reflect_Audio_Journaling/Frontend/node_modules/.bin/next"

rm -rf Frontend/.next

cd "$(dirname "$0")"
echo "🚀 Starting REFLECT Engine..."

# -----------------------------
# Conda environment setup
# -----------------------------
if command -v conda >/dev/null 2>&1; then
    echo "[Info] Conda detected."
    # shellcheck disable=SC1091
    source "$(conda info --base)/etc/profile.d/conda.sh"

    # Activate the reflect environment
    if conda info --envs | grep -q '^reflect'; then
        echo "[Info] Activating 'reflect' environment..."
        conda activate reflect
    else
        echo "[Error] Conda environment 'reflect' not found. Please run setup.command first."
        exit 1
    fi
else
    echo "[Warning] Conda not found. Running in current Python environment."
fi

# -----------------------------
# Verify Python & pip
# -----------------------------
echo "[Info] Python executable: $(which python)"
python --version
python -m pip --version || echo "[Warning] pip not found in this environment!"

# -----------------------------
# Check critical dependencies
# -----------------------------
echo "[Info] Checking critical Python packages..."
python -c "import torch" 2>/dev/null || { 
    echo "[Error] PyTorch not installed in this environment!"
    echo "Run 'python -m pip install torch torchvision torchaudio' inside the 'reflect' environment."
    exit 1
}

# -----------------------------
# Start Backend in background
# -----------------------------
echo "[Supervisor] Starting Backend Engine..."
cd Backend/app
python dev.py &
BACKEND_PID=$!
echo "[Info] Backend PID: $BACKEND_PID"

# -----------------------------
# Start Frontend
# -----------------------------
cd ../../Frontend
echo "[Supervisor] Starting Frontend..."
npm run dev &

# -----------------------------
# Wait and open browser
# -----------------------------
echo "[Info] Waiting a few seconds for server to start..."
sleep 5

echo "[Info] Opening browser at http://localhost:3000..."
open "http://localhost:3000" 2>/dev/null || xdg-open "http://localhost:3000" 2>/dev/null &

# -----------------------------
# Keep terminal attached to backend
# -----------------------------
wait $BACKEND_PID
