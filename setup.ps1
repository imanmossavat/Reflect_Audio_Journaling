# -----------------------------------------
# REFLECT Auto-Setup (Windows PowerShell)
# Fully Conda-aware with verbose output
# -----------------------------------------

$Host.UI.RawUI.WindowTitle = "Reflect Project Setup"
Set-Location $PSScriptRoot
Write-Host "Starting REFLECT Auto-Setup..." -ForegroundColor Cyan
Write-Host ""

# -----------------------------
# Conda Environment Setup
# -----------------------------
$condaPath = Get-Command conda -ErrorAction SilentlyContinue

if ($condaPath) {
    Write-Host "[Info] Conda detected at: $($condaPath.Source)" -ForegroundColor Green
    
    # Initialize Conda for this PowerShell session
    $condaBase = (conda info --base)
    . "$condaBase\shell\condabin\conda-hook.ps1"
    
    # Check if 'reflect' environment exists
    $envList = (conda info --envs) -join "`n"
    if ($envList -notmatch "\breflect\b") {
        Write-Host "[Info] Creating Conda environment 'reflect' with Python 3.10..." -ForegroundColor Yellow
        conda create -n reflect python=3.10 -y
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[Error] Failed to create Conda environment." -ForegroundColor Red
            Read-Host "Press Enter to exit"
            exit 1
        }
    } else {
        Write-Host "[Info] Conda environment 'reflect' already exists." -ForegroundColor Green
    }
    
    Write-Host "[Info] Activating Conda environment 'reflect'..." -ForegroundColor Cyan
    conda activate reflect
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[Error] Failed to activate Conda environment." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    
    Write-Host ""
    Write-Host "[Info] Python executable: $(Get-Command python | Select-Object -ExpandProperty Source)" -ForegroundColor Green
    Write-Host "[Info] Python version: $(python --version)" -ForegroundColor Green
    Write-Host "[Info] Pip version: $(python -m pip --version)" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "[Warning] Conda not found. Using system Python." -ForegroundColor Yellow
    Write-Host "[Info] For best results, install Miniconda/Anaconda and run this script again." -ForegroundColor Yellow
    Write-Host ""
}

# -----------------------------
# Run Python Setup Script
# -----------------------------
Write-Host "[Info] Running setup_project.py..." -ForegroundColor Cyan
python setup_project.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[Error] Setup failed. Make sure Python is installed and compatible (>=3.10)." -ForegroundColor Red
}

Write-Host ""
Write-Host "Setup script finished!" -ForegroundColor Green
Read-Host "Press Enter to close"
