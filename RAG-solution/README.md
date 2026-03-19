# 🧠 REFLECT – RAG-Based Reflection Engine (Development)

This module contains the **LLM-powered version of REFLECT**, focused on deeper reflection through Retrieval-Augmented Generation (RAG).

Unlike the basic version, this implementation uses **local AI models** to:
- analyze journal content
- retrieve relevant context
- guide users through structured reflection (e.g. Gibbs cycle)

All processing remains **fully local and privacy-first**.


## ⚠️ Status
This module is **under active development**.

- Core RAG pipeline is implemented
- Reflection support is functional
- Integration with full pipeline (transcription, PII, etc.) is planned


## 🧠 Key Features

### 📥 Journal Ingestion
- Upload journal entries manually
- Text is processed and prepared for AI analysis


### ✂️ Topic Segmentation
- Journals are split into **semantic topics** (not just fixed chunks)
- Uses local LLMs for more meaningful structure


### 🧩 Vector Storage (Chroma)
- Topics are embedded and stored in a **vector database (Chroma)**
- Enables efficient semantic retrieval


### 🔍 Retrieval-Augmented Generation (RAG)
- Relevant journal segments are retrieved based on context
- Provides grounded input for the LLM


### 🧠 Reflection Support (LLM)
Using local models via Ollama, the system can:

- Ask **clarifying questions**
- Help expand on vague thoughts
- Guide users through a **Gibbs reflection cycle**
- Encourage deeper and more structured reflection


### 🔒 Privacy First
- Runs entirely locally via Ollama
- No external API calls
- No data leaves the user’s machine


## ⚙️ Tech Stack

- **LLM Runtime:** Ollama  
- **Models:** qwen3.5:4b (default)  
- **RAG Framework:** LlamaIndex  
- **Vector DB:** Chroma  
- **Backend:** FastAPI  
- **Frontend:** React (Vite)


## 🧠 Install Ollama

REFLECT uses a local AI model via Ollama.

1. Install Ollama: https://ollama.com  
2. Pull the model:

```bash
ollama pull qwen3.5:4b  
ollama pull llama3:8b
ollama pull nomic-embed-text
```

## 🚀 Getting Started With The Terminal

You'll need **two terminals** open — one for the backend, one for the frontend.


## 1. Backend Setup

```bash
cd Backend
```

### Create & activate the Conda environment

```bash
conda env create -f environment.yml
conda activate REFLECT
```

> If you don't have Conda, install it from [conda.io](https://docs.conda.io/en/latest/miniconda.html)

### Create the local database

```bash
alembic upgrade head
```

### Run the backend

```bash
uvicorn app.main:app --reload
```

The backend will start on `http://localhost:8000`

---

## 2. Frontend Setup

Open a **second terminal**, then:

```bash
cd Frontend
```

### Install dependencies

```bash
npm install
```

### Run the frontend

```bash
npm run dev
```

The app will be available at `http://localhost:3000`

---

## ✅ You're all set!

Open your browser and go to **http://localhost:3000**

Both terminals need to stay open while using the app.