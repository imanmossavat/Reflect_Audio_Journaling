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
$certFile = "$certsDir\localhost.pem"
$keyFile  = "$certsDir\localhost-key.pem"

if (-not (Get-Command mkcert -ErrorAction SilentlyContinue)) {
    Write-Host "Installing mkcert..."
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install --id FiloSottile.mkcert -e --silent --accept-package-agreements --accept-source-agreements
        Refresh-Path
    } else {
        Write-Warning "winget not available - install mkcert manually: https://github.com/FiloSottile/mkcert/releases"
    }
}

if (Get-Command mkcert -ErrorAction SilentlyContinue) {
    # Collect every IPv4 address bound to this machine, minus loopback and APIPA.
    # Browsers reject the cert if the hostname/IP isn't in the SAN list, so the
    # set has to track whichever network we're currently on.
    $lanIps = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } |
        Select-Object -ExpandProperty IPAddress)
    $certNames = @("localhost", "127.0.0.1") + $lanIps

    $needsRegen = $true
    if (Test-Path $certFile) {
        try {
            $existing = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($certFile)
            $sanExt = $existing.Extensions | Where-Object { $_.Oid.Value -eq "2.5.29.17" }
            if ($sanExt) {
                $sanText = $sanExt.Format($false)
                $needsRegen = $false
                foreach ($name in $certNames) {
                    if ($sanText -notmatch [regex]::Escape($name)) { $needsRegen = $true; break }
                }
            }
        } catch { $needsRegen = $true }
    }

    if ($needsRegen) {
        $caInstalled = Get-ChildItem Cert:\CurrentUser\Root -ErrorAction SilentlyContinue |
            Where-Object { $_.Subject -like "*mkcert*" }
        if (-not $caInstalled) {
            Write-Host "Installing mkcert local CA (UAC prompt will appear)..."
            Start-Process mkcert -ArgumentList "-install" -Verb RunAs -Wait
        }
        New-Item -ItemType Directory -Force -Path $certsDir | Out-Null
        Write-Host "Generating HTTPS cert for: $($certNames -join ', ')"
        Push-Location $certsDir
        & mkcert -cert-file localhost.pem -key-file localhost-key.pem @certNames
        Pop-Location
    }
    Write-Host "mkcert: OK"
}

$useTls = Test-Path $certFile

# 4. Backend deps + DB migration
Set-Location "$root\Backend"

# Pick PyTorch wheels based on whether an NVIDIA GPU is reachable.
$torchExtra = "cpu"
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    try {
        & nvidia-smi *> $null
        if ($LASTEXITCODE -eq 0) { $torchExtra = "cuda" }
    } catch { }
}
Write-Host "Syncing Python dependencies (torch=$torchExtra)..."
uv sync --extra $torchExtra

# torchcodec on Windows dlopens FFmpeg shared libs (avcodec-61.dll, etc.). The pip
# wheel does not bundle them and winget's ffmpeg is static-only, so without this
# whisperx falls back to a slower path and prints a long UserWarning every run.
# Drop the DLLs next to libtorchcodec_core7.dll -- the loader checks that dir first.
$torchcodecDir = "$root\Backend\.venv\Lib\site-packages\torchcodec"
$ffmpegSentinel = "$torchcodecDir\avcodec-61.dll"
if ((Test-Path $torchcodecDir) -and -not (Test-Path $ffmpegSentinel)) {
    Write-Host "Installing FFmpeg 7 shared DLLs for torchcodec..."
    try {
        $headers = @{ "User-Agent" = "REFLECT-setup" }
        $release = Invoke-RestMethod "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/tags/latest" -Headers $headers
        $asset = $release.assets |
            Where-Object { $_.name -match "^ffmpeg-n7\..*-win64-gpl-shared-.*\.zip$" } |
            Select-Object -First 1
        if ($null -eq $asset) {
            Write-Warning "No FFmpeg 7 shared build found in BtbN latest release -- skipping."
        } else {
            $tmp = Join-Path $env:TEMP "reflect-ffmpeg-$([guid]::NewGuid())"
            New-Item -ItemType Directory -Force -Path $tmp | Out-Null
            $zipPath = Join-Path $tmp $asset.name
            Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zipPath -UseBasicParsing
            Expand-Archive -Path $zipPath -DestinationPath $tmp -Force
            $extracted = Get-ChildItem -Path $tmp -Directory -Filter "ffmpeg-n7*" | Select-Object -First 1
            if ($extracted) {
                Get-ChildItem -Path (Join-Path $extracted.FullName "bin") -Filter "*.dll" |
                    Copy-Item -Destination $torchcodecDir -Force
                Write-Host "ffmpeg DLLs: OK"
            }
            Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
        }
    } catch {
        Write-Warning "FFmpeg DLL install failed: $_"
        Write-Warning "torchcodec will warn at startup but whisperx still works via fallback."
    }
}

Write-Host "Running database migrations..."
uv run --extra $torchExtra alembic upgrade head

# 5. Start backend in a new window 
Write-Host "Starting backend..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\Backend'; uv run --extra $torchExtra python start_backend.py"

# 6. Frontend deps + start
Set-Location "$root\frontend"
# Always run npm install -- it's a fast no-op when the lockfile already matches,
# and it ensures newly added deps are picked up on re-runs.
Write-Host "Installing frontend dependencies..."
npm install
Write-Host "Starting frontend..."
$frontendScript = if ($useTls) { "npm run dev:tls" } else { "npm run dev" }
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\frontend'; $frontendScript"

$scheme = if ($useTls) { "https" } else { "http" }
Write-Host ""
Write-Host "Both servers are starting."
Write-Host "Open ${scheme}://localhost:3000 in your browser."
