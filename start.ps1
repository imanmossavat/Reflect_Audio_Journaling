# REFLECT startup script - Windows
# Installs uv, Node.js, and mkcert if missing, then starts backend + frontend.

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

function Refresh-Path {
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("PATH", "User")
}

# 1. uv
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv..."
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    Refresh-Path
}
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error "uv install failed. Please install manually: https://docs.astral.sh/uv/getting-started/installation/"
}
Write-Host "uv: OK"

# 2. Node.js
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Node.js via winget..."
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install --id OpenJS.NodeJS.LTS -e --silent --accept-package-agreements --accept-source-agreements
        Refresh-Path
    } else {
        Write-Error "winget not available. Please install Node.js manually: https://nodejs.org"
    }
}
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Error "Node.js install failed. Please install manually: https://nodejs.org"
}
Write-Host "node: OK"

# 3. mkcert + HTTPS certificates
$certsDir = "$root\certs"
$certFile = "$certsDir\localhost+1.pem"

if (-not (Get-Command mkcert -ErrorAction SilentlyContinue)) {
    Write-Host "Installing mkcert..."
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install --id FiloSottile.mkcert -e --silent --accept-package-agreements --accept-source-agreements
        Refresh-Path
    } else {
        Write-Warning "winget not available - install mkcert manually: https://github.com/FiloSottile/mkcert/releases"
    }
}

if ((Get-Command mkcert -ErrorAction SilentlyContinue) -and (-not (Test-Path $certFile))) {
    Write-Host "Setting up local HTTPS certificates (a UAC prompt will appear to trust the CA)..."
    Start-Process mkcert -ArgumentList "-install" -Verb RunAs -Wait
    New-Item -ItemType Directory -Force -Path $certsDir | Out-Null
    Push-Location $certsDir
    & mkcert localhost 127.0.0.1
    Pop-Location
    Write-Host "Certificates ready."
} else {
    Write-Host "mkcert: OK"
}

$useTls = Test-Path $certFile

# 4. Backend deps + DB migration
Set-Location "$root\Backend"
Write-Host "Syncing Python dependencies..."
uv sync
Write-Host "Running database migrations..."
uv run alembic upgrade head

# 5. Start backend in a new window 
Write-Host "Starting backend..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\Backend'; uv run python start_backend.py"

# 6. Frontend deps + start 
Set-Location "$root\frontend"
if (-not (Test-Path "node_modules\.bin")) {
    Write-Host "Installing frontend dependencies..."
    npm install
}
Write-Host "Starting frontend..."
$frontendScript = if ($useTls) { "npm run dev:tls" } else { "npm run dev" }
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\frontend'; $frontendScript"

$scheme = if ($useTls) { "https" } else { "http" }
Write-Host ""
Write-Host "Both servers are starting."
Write-Host "Open ${scheme}://localhost:3000 in your browser."
