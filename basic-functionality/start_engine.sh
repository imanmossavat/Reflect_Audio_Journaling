#!/bin/bash
cd "$(dirname "$0")"

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

if [ -d "$HOME/.pyenv" ]; then
    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init --path)"
    eval "$(pyenv init -)"
fi

[ -f "$HOME/.profile" ] && source "$HOME/.profile"
[ -f "$HOME/.bashrc" ] && source "$HOME/.bashrc"

open "http://localhost:3000" 2>/dev/null || xdg-open "http://localhost:3000" 2>/dev/null &

cd Backend/app
if [ -f "../.venv/bin/python" ]; then
    ../.venv/bin/python dev.py
else
    python3 dev.py || python dev.py
fi