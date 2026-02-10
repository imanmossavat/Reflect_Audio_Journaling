# -----------------------------------------
# REFLECT Quick Start (Windows PowerShell)
# Fully Conda-aware
# Backend runs with frontend, browser opens automatically
# -----------------------------------------

$Host.UI.RawUI.WindowTitle = "Reflect Command Center"
Set-Location $PSScriptRoot
Write-Host "Starting REFLECT Engine..." -ForegroundColor Cyan
Write-Host ""

# -----------------------------
# Kill old processes
# -----------------------------
Write-Host "[Info] Cleaning up old processes..." -ForegroundColor Yellow
Get-Process -Name "python" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process -Name "node" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

# Clean up .next folder for fresh start
if (Test-Path "Frontend\.next") {
    Write-Host "[Info] Removing old .next build folder..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force "Frontend\.next" -ErrorAction SilentlyContinue
}

# -----------------------------
# Conda Environment Setup
# -----------------------------
$condaPath = Get-Command conda -ErrorAction SilentlyContinue

if ($condaPath) {
    Write-Host "[Info] Conda detected." -ForegroundColor Green
    
    # Initialize Conda for this PowerShell session
    $condaBase = (conda info --base)
    . "$condaBase\shell\condabin\conda-hook.ps1"
    
    # Check if 'reflect' environment exists
    $envList = (conda info --envs) -join "`n"
    if ($envList -notmatch "\breflect\b") {
        Write-Host "[Error] Conda environment 'reflect' not found. Please run setup.bat first." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    
    Write-Host "[Info] Activating Conda environment 'reflect'..." -ForegroundColor Cyan
    conda activate reflect
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[Error] Failed to activate Conda environment." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    
    Write-Host "[Info] Python executable: $(Get-Command python | Select-Object -ExpandProperty Source)" -ForegroundColor Green
    Write-Host "[Info] Python version: $(python --version)" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "[Warning] Conda not found. Using system Python." -ForegroundColor Yellow
    Write-Host "[Warning] For best results, install Miniconda/Anaconda." -ForegroundColor Yellow
    Write-Host ""
}

# -----------------------------
# Check critical dependencies
# -----------------------------
Write-Host "[Info] Checking critical Python packages..." -ForegroundColor Cyan

python -c "import torch" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[Error] PyTorch not installed in this environment!" -ForegroundColor Red
    Write-Host "[Error] Run 'pip install torch torchvision torchaudio' inside the 'reflect' environment." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "[Info] PyTorch OK" -ForegroundColor Green

python -c "import transformers" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[Warning] Transformers not installed. Some features may not work." -ForegroundColor Yellow
} else {
    Write-Host "[Info] Transformers OK" -ForegroundColor Green
}
Write-Host ""

# -----------------------------
# Start Backend (dev.py handles Frontend too)
# -----------------------------
Write-Host "[Supervisor] Starting Backend Engine..." -ForegroundColor Cyan

# Wait a few seconds then open browser
Start-Job -ScriptBlock {
    Start-Sleep -Seconds 5
    Start-Process "http://localhost:3000"
} | Out-Null

Set-Location "$PSScriptRoot\Backend\app"
python dev.py

Read-Host "Press Enter to close"
