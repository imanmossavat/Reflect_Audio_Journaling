# REFLECT – Your Private AI Audio Journal
A private, local tool for recording your thoughts and getting AI-powered insights — without your data ever leaving your computer.

---

## Contents

- [How the AI works](#how-the-ai-works-and-why-its-private)
- [Prerequisites](#prerequisites-one-time-setup)
- [Run](#run)
- [Updates](#updates)
- [Legacy version](#legacy-version)
- [Tech Stack](#tech-stack)

---

## How the AI works (and why it's private)

REFLECT uses **open-weights AI models**. This is the same kind of technology behind large cloud AI services, except the model files live on your own machine. "Open weights" means the decision-making parameters of the model are publicly available and can be downloaded like any other file.

When you talk to REFLECT, every word is processed locally. Nothing is sent to a server, no API key is required, and no company can read your journal. Your thoughts stay yours.

---

## Prerequisites (one-time setup)

**1. Install Ollama**

Ollama runs AI models locally on your computer. Download it from [ollama.com](https://ollama.com) and install it.

**2. Pull the required models**

This downloads the open-weights model files (~5 GB total). Run these commands once:

```bash
ollama pull gemma4:e4b
ollama pull nomic-embed-text
```

These files stay on your machine. Nothing is uploaded.

**3. Make sure Ollama is running**

Ollama needs to be running whenever you use REFLECT. If it isn't already running as a background service, start it with:

```bash
ollama serve
```

You can check by opening [http://localhost:11434](http://localhost:11434) — if it responds, you're good.

Everything else (uv, Node.js, Python dependencies) is installed automatically by the startup script.

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

Then open **https://localhost:3000** in your browser.

> **First run takes a few minutes** — the script installs Python and Node dependencies automatically. Subsequent starts are fast.

---

## Updates

To get the latest version, pull from git and run the start script again.

**Windows:**
```powershell
git pull
.\start.ps1
```

**Mac/Linux:**
```bash
git pull
./start.sh
```

---

## Legacy version

An older prototype is preserved in the [`legacy`](../../tree/legacy) branch.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript |
| UI | Tailwind CSS v4, shadcn/ui (Radix UI), TipTap editor, Recharts, React Hook Form + Zod |
| Backend | FastAPI, Uvicorn, Pydantic, SQLite, SQLModel, Alembic |
| ML / audio | PyTorch (CPU/CUDA), librosa, Hugging Face Transformers |
| Transcription | WhisperX (faster-whisper + pyannote-audio diarization) |
| LLM inference | Ollama (local, open-weights) |
| RAG | LlamaIndex, ChromaDB, nomic-embed-text, sentence-transformers (reranking) |
| NLP | spaCy (English + Dutch) |
| Evaluation | RAGAS |
| Tooling | uv (Python), npm / Node.js |
