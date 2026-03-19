#!/bin/bash
cd "$(dirname "$0")"
echo "Starting REFLECT Auto-Setup..."
python3 setup_project.py || python setup_project.py
if [ $? -ne 0 ]; then
    echo ""
    echo "[Error] Setup failed. Make sure Python is installed."
fi
echo ""
echo "Press any key to close..."
read -n 1
