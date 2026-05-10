# REFLECT – Your Private AI Audio Journal

A private, local tool for recording your thoughts and getting AI-powered insights — without your data ever leaving your computer.

---

## Prerequisites (one-time)

**Ollama** — local AI models:
1. Download and install: https://ollama.com
2. Pull the required models:
   ```bash
   ollama pull gemma4:e4b
   ollama pull nomic-embed-text
   ```
3. Keep Ollama running in the background while using REFLECT.

Everything else (uv, Node.js) is installed automatically by the startup script.

---

## Run

**Windows:**
```powershell
.\start.ps1
```

**Mac/Linux:**
```bash
chmod +x start.sh && ./start.sh
```

Then open **http://localhost:3000** in your browser.

On first run the script will install dependencies — this takes a few minutes. Subsequent runs are fast.

---

## Restarting

Run the same command again. Dependency installs are skipped if already present.
