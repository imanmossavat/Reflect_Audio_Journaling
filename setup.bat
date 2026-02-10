@echo off
:: This batch file launches the setup in PowerShell where Conda is available
title Reflect Project Setup
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -NoExit -File "%~dp0setup.ps1"
