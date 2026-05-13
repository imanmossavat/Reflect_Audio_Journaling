#!/usr/bin/env bash
# REFLECT startup script — Mac/Linux
# Installs uv, Node.js, and mkcert if missing, then starts backend + frontend.

set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. uv 
if ! command -v uv &>/dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    if [ -f "$HOME/.local/bin/env" ]; then
        source "$HOME/.local/bin/env"
    else
        export PATH="$HOME/.local/bin:$PATH"
    fi
fi
if ! command -v uv &>/dev/null; then
    echo "uv install failed. Please install manually: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi
echo "uv: OK"

# 2. Node.js (via fnm) 
if ! command -v node &>/dev/null; then
    echo "Installing fnm (Node version manager)..."
    curl -fsSL https://fnm.vercel.app/install | bash
    export PATH="$HOME/.local/share/fnm:$PATH"
    eval "$(fnm env --use-on-cd 2>/dev/null || true)"
    fnm install --lts
    fnm use lts-latest
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

if ! command -v mkcert &>/dev/null; then
    echo "Installing mkcert..."
    if command -v brew &>/dev/null; then
        brew install mkcert
    elif command -v apt-get &>/dev/null; then
        sudo apt-get install -y libnss3-tools
        curl -JLO "https://github.com/FiloSottile/mkcert/releases/latest/download/mkcert-v$(curl -s https://api.github.com/repos/FiloSottile/mkcert/releases/latest | grep tag_name | cut -d'"' -f4 | tr -d v)-linux-amd64"
        chmod +x mkcert-*-linux-amd64 && sudo mv mkcert-*-linux-amd64 /usr/local/bin/mkcert
    else
        echo "Warning: could not install mkcert automatically."
        echo "Install manually from https://github.com/FiloSottile/mkcert/releases"
    fi
fi

if command -v mkcert &>/dev/null; then
    # Collect every IPv4 address bound to this machine, minus loopback and APIPA.
    # Browsers reject the cert if the hostname/IP isn't in the SAN list, so the
    # set has to track whichever network we're currently on.
    if command -v ip &>/dev/null; then
        LAN_IPS=$(ip -4 -o addr show scope global 2>/dev/null | awk '{print $4}' | cut -d/ -f1)
    else
        LAN_IPS=$(ifconfig 2>/dev/null | awk '/inet / {print $2}' | grep -Ev '^(127\.|169\.254\.)')
    fi
    CERT_NAMES=("localhost" "127.0.0.1")
    for ip in $LAN_IPS; do
        CERT_NAMES+=("$ip")
    done

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
        # Without openssl we can't inspect SANs; trust the existing cert.
        NEEDS_REGEN=false
    fi

    if $NEEDS_REGEN; then
        if ! mkcert -CAROOT &>/dev/null || [ ! -f "$(mkcert -CAROOT)/rootCA.pem" ]; then
            echo "Installing mkcert local CA (may prompt for sudo)..."
            mkcert -install
        fi
        mkdir -p "$CERTS_DIR"
        echo "Generating HTTPS cert for: ${CERT_NAMES[*]}"
        cd "$CERTS_DIR"
        mkcert -cert-file localhost.pem -key-file localhost-key.pem "${CERT_NAMES[@]}"
        cd "$ROOT"
    fi
    echo "mkcert: OK"
fi

USE_TLS=false
[ -f "$CERT_FILE" ] && USE_TLS=true

# 4. Backend deps + DB migration
cd "$ROOT/Backend"
echo "Syncing Python dependencies..."
uv sync
echo "Running database migrations..."
uv run alembic upgrade head

# 5. Start backend in background
echo "Starting backend..."
uv run python start_backend.py &
BACKEND_PID=$!

# 6. Frontend deps + start
cd "$ROOT/frontend"
if [ ! -d "node_modules/.bin" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi
echo "Starting frontend..."
if $USE_TLS; then
    npm run dev:tls &
else
    npm run dev &
fi
FRONTEND_PID=$!

SCHEME="http"
$USE_TLS && SCHEME="https"

echo ""
echo "Both servers are starting."
echo "Open $SCHEME://localhost:3000 in your browser."
echo "Press Ctrl+C to stop both servers."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait $BACKEND_PID $FRONTEND_PID
