# REFLECT startup script — Windows
# Installs uv and Node.js if missing, then starts backend + frontend.

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

function Refresh-Path {
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("PATH", "User")
}

# ── 1. uv ────────────────────────────────────────────────────────────────────
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv..."
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    Refresh-Path
}
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error "uv install failed. Please install manually: https://docs.astral.sh/uv/getting-started/installation/"
}
Write-Host "uv: OK"

# ── 2. Node.js ───────────────────────────────────────────────────────────────
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

# ── 3. Backend deps + DB migration ───────────────────────────────────────────
Set-Location "$root\Backend"
Write-Host "Syncing Python dependencies..."
uv sync
Write-Host "Running database migrations..."
uv run alembic upgrade head

# ── 4. Start backend in a new window ─────────────────────────────────────────
Write-Host "Starting backend..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\Backend'; uv run python start_backend.py"

# ── 5. Frontend deps + start ─────────────────────────────────────────────────
Set-Location "$root\Frontend"
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing frontend dependencies..."
    npm install
}
Write-Host "Starting frontend..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\Frontend'; npm run dev"

Write-Host ""
Write-Host "Both servers are starting."
Write-Host "Open http://localhost:3000 in your browser."
