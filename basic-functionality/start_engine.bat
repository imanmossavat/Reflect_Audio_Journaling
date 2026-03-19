@echo off
title Reflect Command Center

:: Wait a few seconds for the engine to start before opening the browser
start "" "http://localhost:3000"

cd /d "%~dp0Backend\app"
python dev.py
pause