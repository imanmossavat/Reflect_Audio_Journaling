@echo off
title Reflect Project Setup
echo Starting REFLECT Auto-Setup...
python setup_project.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [Error] Setup failed. Make sure Python is installed and in your PATH.
)
pause
