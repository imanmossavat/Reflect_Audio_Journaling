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
    fnm use --lts
fi
if ! command -v node &>/dev/null; then
    echo "Node.js install failed. Please install manually: https://nodejs.org"
    exit 1
fi
echo "node: OK"

# 3. mkcert + HTTPS certificates
CERTS_DIR="$ROOT/certs"
CERT_FILE="$CERTS_DIR/localhost+1.pem"

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

if command -v mkcert &>/dev/null && [ ! -f "$CERT_FILE" ]; then
    echo "Setting up local HTTPS certificates (may prompt for sudo to trust the CA)..."
    mkcert -install
    mkdir -p "$CERTS_DIR"
    cd "$CERTS_DIR"
    mkcert localhost 127.0.0.1
    cd "$ROOT"
    echo "Certificates ready."
else
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
