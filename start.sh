#!/usr/bin/env bash
# REFLECT startup script — Mac/Linux
# Installs uv, Node.js, and mkcert if missing, then starts backend + frontend.

set -e
trap 'echo "Error at line $LINENO (exit code $?)" >&2' ERR

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Add known tool install dirs to PATH up front so re-runs skip reinstalls.
export PATH="$HOME/.local/bin:$HOME/.local/share/fnm:$PATH"

# Add fnm's latest installed node version to PATH by scanning the filesystem
# (avoids `eval "$(fnm env)"` which can inject shell-specific commands like `rehash`).
_NODE_BIN=$(ls -1d "$HOME/.local/share/fnm/node-versions/"*/installation/bin 2>/dev/null \
    | sort -V | tail -1)
if [ -n "$_NODE_BIN" ]; then
    export PATH="$_NODE_BIN:$PATH"
fi

# 1. uv
if ! command -v uv &>/dev/null; then
    echo "Installing uv..."
    UV_INSTALL_DIR="$HOME/.local/bin" curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
if ! command -v uv &>/dev/null; then
    echo "uv install failed. Please install manually: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi
echo "uv: OK"

# 2. Node.js (via fnm)
if ! command -v node &>/dev/null; then
    echo "Installing fnm (Node version manager)..."
    curl -fsSL https://fnm.vercel.app/install | bash || true
    export PATH="$HOME/.local/share/fnm:$PATH"
    fnm install --lts
    fnm default lts-latest
    # Add the newly installed node to PATH
    _NODE_BIN=$(ls -1d "$HOME/.local/share/fnm/node-versions/"*/installation/bin 2>/dev/null \
        | sort -V | tail -1)
    if [ -n "$_NODE_BIN" ]; then
        export PATH="$_NODE_BIN:$PATH"
    fi
fi
if ! command -v node &>/dev/null; then
    echo "Node.js install failed. Please install manually: https://nodejs.org"
    exit 1
fi
echo "node: OK"

# 3. mkcert + HTTPS certificates
CERTS_DIR="$ROOT/certs"
CERT_FILE="$CERTS_DIR/localhost.pem"
KEY_FILE="$CERTS_DIR/localhost-key.pem"

# Remove any previously corrupt mkcert binary (e.g. a saved HTML 404 page).
if [ -f "$HOME/.local/bin/mkcert" ]; then
    if ! "$HOME/.local/bin/mkcert" --version &>/dev/null; then
        echo "Removing invalid mkcert binary, re-downloading..."
        rm -f "$HOME/.local/bin/mkcert"
    fi
fi

if ! command -v mkcert &>/dev/null; then
    echo "Installing mkcert..."
    if command -v brew &>/dev/null; then
        brew install mkcert
    else
        # Try to install nss-tools for Firefox support (optional, non-fatal)
        if command -v dnf &>/dev/null; then
            sudo dnf install -y nss-tools 2>/dev/null || true
        elif command -v apt-get &>/dev/null; then
            sudo apt-get install -y libnss3-tools 2>/dev/null || true
        fi
        # Download mkcert binary using the versioned release URL (-f fails on HTTP errors)
        MKCERT_VER=$(curl -fsSL "https://api.github.com/repos/FiloSottile/mkcert/releases/latest" \
            | grep '"tag_name"' | cut -d'"' -f4 | tr -d 'v ')
        if [ -n "$MKCERT_VER" ]; then
            mkdir -p "$HOME/.local/bin"
            if curl -fLo "$HOME/.local/bin/mkcert" \
                "https://github.com/FiloSottile/mkcert/releases/download/v${MKCERT_VER}/mkcert-v${MKCERT_VER}-linux-amd64"; then
                chmod +x "$HOME/.local/bin/mkcert"
            else
                echo "Warning: mkcert download failed. HTTPS/microphone unavailable."
                rm -f "$HOME/.local/bin/mkcert"
            fi
        else
            echo "Warning: could not determine mkcert version (GitHub API rate limit?). HTTPS unavailable."
        fi
    fi
fi

if command -v mkcert &>/dev/null; then
    detect_primary_ip() {
        local py=""
        if command -v python3 &>/dev/null; then py="python3"
        elif command -v python &>/dev/null; then py="python"
        elif command -v uv &>/dev/null; then py="uv run --no-project --quiet python"
        else return
        fi
        $py -c 'import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    s.connect(("8.8.8.8", 80))
    print(s.getsockname()[0])
except Exception:
    pass
finally:
    s.close()' 2>/dev/null
    }

    LAN_IPS=""
    PRIMARY_IP=$(detect_primary_ip || true)
    if [ -n "$PRIMARY_IP" ] && [ "$PRIMARY_IP" != "127.0.0.1" ]; then
        LAN_IPS="$PRIMARY_IP"
    fi
    if command -v ip &>/dev/null; then
        EXTRA_IPS=$(ip -4 -o addr show scope global 2>/dev/null | awk '{print $4}' | cut -d/ -f1 || true)
    else
        EXTRA_IPS=$(ifconfig 2>/dev/null | awk '/inet / {print $2}' | grep -Ev '^(127\.|169\.254\.)' || true)
    fi
    for ip in $EXTRA_IPS; do
        case " $LAN_IPS " in *" $ip "*) ;; *) LAN_IPS="$LAN_IPS $ip" ;; esac
    done

    CERT_NAMES=("localhost" "127.0.0.1")
    for ip in $LAN_IPS; do
        CERT_NAMES+=("$ip")
    done

    if [ -z "$LAN_IPS" ]; then
        echo "Warning: could not detect LAN IP — cert will cover localhost only."
    fi

    NEEDS_REGEN=true
    if [ -f "$CERT_FILE" ] && command -v openssl &>/dev/null; then
        SAN_TEXT=$(openssl x509 -in "$CERT_FILE" -noout -ext subjectAltName 2>/dev/null || true)
        if [ -n "$SAN_TEXT" ]; then
            NEEDS_REGEN=false
            for name in "${CERT_NAMES[@]}"; do
                if ! echo "$SAN_TEXT" | grep -qF "$name"; then
                    NEEDS_REGEN=true
                    break
                fi
            done
        fi
    elif [ -f "$CERT_FILE" ]; then
        NEEDS_REGEN=false
    fi

    if [ "$NEEDS_REGEN" = true ]; then
        CAROOT=$(mkcert -CAROOT 2>/dev/null || true)
        if [ -z "$CAROOT" ] || [ ! -f "$CAROOT/rootCA.pem" ]; then
            echo "Installing mkcert local CA (may prompt for sudo)..."
            mkcert -install || true
        fi
        mkdir -p "$CERTS_DIR"
        echo "Generating HTTPS cert for: ${CERT_NAMES[*]}"
        cd "$CERTS_DIR"
        mkcert -cert-file localhost.pem -key-file localhost-key.pem "${CERT_NAMES[@]}"
        cd "$ROOT"
    fi
    # Run mkcert -install (idempotent) and parse its output to determine trust status.
    INSTALL_OUT=$(mkcert -install 2>&1 || true)
    NEEDS_NSS=false
    NEEDS_INSTALL=false
    if echo "$INSTALL_OUT" | grep -qi "certutil.*not available"; then
        NEEDS_NSS=true
    elif ! echo "$INSTALL_OUT" | grep -qi "already installed\|installed in the system"; then
        NEEDS_INSTALL=true
    fi

    if [ "$NEEDS_NSS" = false ] && [ "$NEEDS_INSTALL" = false ]; then
        echo "mkcert: OK"
    elif [ "$NEEDS_NSS" = true ]; then
        echo "mkcert: OK (system CA installed — browser trust needs nss-tools)"
        printf '\n\033[1;33m╔══════════════════════════════════════════════════════════════╗\033[0m\n'
        printf '\033[1;33m║  ACTION REQUIRED — Install nss-tools for browser trust       ║\033[0m\n'
        printf '\033[1;33m╠══════════════════════════════════════════════════════════════╣\033[0m\n'
        printf '\033[1;33m║  The CA is in the system store but Chrome/Firefox need       ║\033[0m\n'
        printf '\033[1;33m║  certutil to register it. Run once in a normal terminal:     ║\033[0m\n'
        printf '\033[1;33m║                                                              ║\033[0m\n'
        printf '\033[1;33m║    \033[1;97msudo dnf install nss-tools && mkcert -install\033[1;33m           ║\033[0m\n'
        printf '\033[1;33m║                                                              ║\033[0m\n'
        printf '\033[1;33m║  Until then: visit https://localhost:3000, click Advanced,   ║\033[0m\n'
        printf '\033[1;33m║  and choose "Proceed anyway" to enable the microphone.       ║\033[0m\n'
        printf '\033[1;33m╚══════════════════════════════════════════════════════════════╝\033[0m\n\n'
    else
        echo "mkcert: certs generated (CA not yet trusted)"
        printf '\n\033[1;33m╔══════════════════════════════════════════════════════════════╗\033[0m\n'
        printf '\033[1;33m║  ACTION REQUIRED — Browser will show a security warning      ║\033[0m\n'
        printf '\033[1;33m╠══════════════════════════════════════════════════════════════╣\033[0m\n'
        printf '\033[1;33m║  To fix this permanently, open a NORMAL terminal and run:    ║\033[0m\n'
        printf '\033[1;33m║                                                              ║\033[0m\n'
        printf '\033[1;33m║    \033[1;97mmkcert -install\033[1;33m                                           ║\033[0m\n'
        printf '\033[1;33m║                                                              ║\033[0m\n'
        printf '\033[1;33m║  Until then: visit https://localhost:3000, click Advanced,   ║\033[0m\n'
        printf '\033[1;33m║  and choose "Proceed anyway" to enable the microphone.       ║\033[0m\n'
        printf '\033[1;33m╚══════════════════════════════════════════════════════════════╝\033[0m\n\n'
    fi
fi

USE_TLS=false
if [ -f "$CERT_FILE" ]; then
    USE_TLS=true
fi

# 4. Backend deps + DB migration
cd "$ROOT/Backend"

# Pick PyTorch wheels based on whether an NVIDIA GPU is reachable.
TORCH_EXTRA="cpu"
if command -v nvidia-smi &>/dev/null && nvidia-smi &>/dev/null; then
    TORCH_EXTRA="cuda"
fi
echo "Syncing Python dependencies (torch=$TORCH_EXTRA)..."
uv sync --extra "$TORCH_EXTRA"

# torchcodec dlopens FFmpeg's shared libs (libavcodec.so / .dylib). On Unix the
# dynamic linker finds them as long as a system FFmpeg ≥ 4 is installed, so the
# right shape here is just a system package install (mirroring nss-tools/mkcert).
if ! command -v ffmpeg &>/dev/null; then
    echo "Installing ffmpeg (required by torchcodec)..."
    if command -v brew &>/dev/null; then
        brew install ffmpeg || true
    elif command -v apt-get &>/dev/null; then
        sudo apt-get install -y ffmpeg 2>/dev/null || true
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y ffmpeg 2>/dev/null || true
    else
        echo "Warning: no supported package manager found. Install ffmpeg manually."
    fi
fi
if command -v ffmpeg &>/dev/null; then
    echo "ffmpeg: OK"
fi

echo "Running database migrations..."
uv run alembic upgrade head

# 5. Start backend in background
echo "Starting backend..."
uv run python start_backend.py &
BACKEND_PID=$!

# 6. Frontend deps + start
cd "$ROOT/frontend"
# Always run npm install — it's a fast no-op when the lockfile already matches,
# and it ensures newly added deps are picked up on re-runs.
echo "Installing frontend dependencies..."
npm install
echo "Starting frontend..."
if [ "$USE_TLS" = true ]; then
    npm run dev:tls &
else
    npm run dev &
fi
FRONTEND_PID=$!

SCHEME="http"
if [ "$USE_TLS" = true ]; then
    SCHEME="https"
fi

echo ""
echo "Both servers are starting."
echo "Open $SCHEME://localhost:3000 in your browser."
echo "Press Ctrl+C to stop both servers."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait $BACKEND_PID $FRONTEND_PID
