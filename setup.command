#!/bin/bash
# -----------------------------------------
# REFLECT Auto-Setup (Mac/Linux)
# Fully Conda-aware with verbose output
# -----------------------------------------

cd "$(dirname "$0")"
echo "Starting REFLECT Auto-Setup..."

# Verbose flag for Python script
export VERBOSE=1

# Detect Conda
if [[ -n "$CONDA_PREFIX" ]]; then
    echo "⚠️ Conda environment detected."
    echo "Conda prefix: $CONDA_PREFIX"

    # Create Conda environment if it doesn't exist
    if ! conda info --envs | grep -q '^reflect'; then
        echo "Creating Conda environment 'reflect' with Python 3.10..."
        conda create -n reflect python=3.10 -y
    fi

    echo "Activating Conda environment..."
    # shellcheck disable=SC1091
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate reflect

    echo "Python executable: $(which python)"
    echo "Python version: $(python --version)"
    echo "Pip version: $(python -m pip --version)"

    # Run Python setup
    python setup_project.py

else
    # Non-Conda: use venv
    if [ ! -d ".venv" ]; then
        echo "Creating virtual environment (.venv) with Python 3.10+..."
        python3 -m venv .venv || python -m venv .venv
    fi

    # Activate venv
    # shellcheck disable=SC1091
    source .venv/bin/activate

    echo "Python executable: $(which python)"
    echo "Python version: $(python --version)"
    echo "Pip version: $(python -m pip --version)"

    # Run Python setup
    python setup_project.py
fi

# Check last command
if [ $? -ne 0 ]; then
    echo ""
    echo "[Error] Setup failed. Make sure Python is installed and compatible (>=3.10)."
fi

echo ""
echo "✅ Setup script finished!"
echo "Press any key to close..."
read -n 1
