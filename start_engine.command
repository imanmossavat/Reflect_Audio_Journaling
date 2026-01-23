#!/bin/bash
cd "$(dirname "$0")"

# Open the browser in the background
open "http://localhost:3000" 2>/dev/null || xdg-open "http://localhost:3000" 2>/dev/null &

cd Backend/app
python3 dev.py || python dev.py