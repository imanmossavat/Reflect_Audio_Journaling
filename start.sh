#!/usr/bin/env bash
# REFLECT startup script — Mac/Linux
# Installs uv and Node.js (via fnm) if missing, then starts backend + frontend.

set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── 1. uv ────────────────────────────────────────────────────────────────────
if ! command -v uv &>/dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Source the env file the installer drops
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

# ── 2. Node.js (via fnm) ─────────────────────────────────────────────────────
if ! command -v node &>/dev/null; then
    echo "Installing fnm (Node version manager)..."
    curl -fsSL https://fnm.vercel.app/install | bash
    # Source fnm into the current shell
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

# ── 3. Backend deps + DB migration ───────────────────────────────────────────
cd "$ROOT/Backend"
echo "Syncing Python dependencies..."
uv sync
echo "Running database migrations..."
uv run alembic upgrade head

# ── 4. Start backend in background ───────────────────────────────────────────
echo "Starting backend..."
uv run python start_backend.py &
BACKEND_PID=$!

# ── 5. Frontend deps + start ─────────────────────────────────────────────────
cd "$ROOT/frontend"
if [ ! -d "node_modules/.bin" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi
echo "Starting frontend..."
npm run dev &
FRONTEND_PID=$!

echo ""
echo "Both servers are starting."
echo "Open http://localhost:3000 in your browser."
echo "Press Ctrl+C to stop both servers."

# Keep script alive; Ctrl+C kills both background jobs
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait $BACKEND_PID $FRONTEND_PID
