# REFLECT — RAG Backend

This folder contains the backend service for the RAG-based REFLECT prototype.

It handles journal ingestion, topic extraction, retrieval, and reflection-question generation while keeping everything local.

---

## Index
1. [What this backend does](#what-this-backend-does)
2. [Folder map](#folder-map)
3. [Quick start (backend only)](#quick-start-backend-only)
4. [Notes for contributors](#notes-for-contributors)

---

## What this backend does
- Accepts uploaded text journals
- Stores journals/chunks in SQLite
- Indexes chunks in Chroma for semantic retrieval
- Uses local LLM tooling (Ollama + LlamaIndex) for query and reflection support
- Exposes FastAPI endpoints consumed by the frontend

---

## Folder map
- **`app/`**: FastAPI app code (routes, schemas, services, prompts).
- **`database/`**: SQLModel table definitions and local Chroma storage files.
- **`migrations/`**: Alembic migration scripts.
- **`environment.yml`**: Conda environment definition.
- **`alembic.ini`**: Alembic configuration.

---

## Quick start (backend only)
From this folder:

```bash
conda env create -f environment.yml
conda activate REFLECT
alembic upgrade head
uvicorn app.main:app --reload
```

Backend default URL: `http://localhost:8000`

Make sure Ollama is running locally when using RAG and generation endpoints.

---

## Notes for contributors
- API entrypoint: `app/main.py`
- SQL models: `database/models.py`
- Main route modules: `app/routes/journal.py` and `app/routes/query.py`
- RAG orchestration: `app/services/rag.py`

When changing DB schema, add an Alembic migration and run it before testing routes.
