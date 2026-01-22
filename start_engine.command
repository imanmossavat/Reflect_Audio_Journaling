#!/bin/bash
cd "$(dirname "$0")"
cd Backend/app
python3 dev.py || python dev.py