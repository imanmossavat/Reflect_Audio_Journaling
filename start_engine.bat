@echo off
:: This batch file launches the engine in PowerShell where Conda is available
title Reflect Command Center
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -NoExit -File "%~dp0start_engine.ps1"