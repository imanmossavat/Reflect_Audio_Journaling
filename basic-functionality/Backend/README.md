# REFLECT — AI Engine (Backend)

This is the "brain" of the project. It uses Artificial Intelligence to listen to your voice and understand what you said.

---

## Index
1. [Simple overview](#simple-overview)
2. [What's inside?](#whats-inside)
3. [One-click setup](#one-click-setup)
4. [Advanced setup](#advanced-setup)
5. [How it works](#how-it-works)
6. [How to update](#how-to-update)

---

## Simple overview
You don't need to touch the code in here to use the app. You just need to make sure this "Engine" is running in the background. 

**Wait, what does it actually do?**
1. **Listens:** It takes your recording and turns it into text (Transcription).
2. **Protects:** It looks for things like your name or phone number so you can hide them (PII Detection).
3. **Organizes:** It groups your talk into chapters (Segmentation).
4. **Feels:** It analyzes the tone of your voice (Prosody).

---

## What's inside?
If you want to explore the files, here is the map:
- **`api/`**: The "Receptionist." This handles the messages coming from the website.
- **`services/`**: The "Specialists." Granular services for specific tasks (storage, prosody, search).
- **`pipelines/`**: The "Assembly Line." This connects the specialists together to process your audio.
- **`data/`**: The "Archive." Local-first storage for metadata, audio, and transcripts.
- **`tests/`**: The "Quality Control." A full suite of automated tests for every service.

---

## Testing
We maintain high code quality with a comprehensive test suite. To run them:
1. Activate your environment.
2. Run `pytest`.
This checks everything from PII detection to file storage integrity.

---

## One-click setup
If you haven't done so yet, go back to the [Main Folder](../) and run:
- **Windows:** `setup.bat`
- **Mac:** `setup.command`

This will automatically create your virtual environment and install all necessary AI models for the backend.

---

## Advanced setup
For the person taking over this project:

### 1. Requirements
Ensure you have **Python 3.10.11**. Consistency is key for AI models.

### 2. Environment
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate
```

### 3. Basic Commands
- `pip install -r requirements.txt` — Install the AI models manually.
- `uvicorn app.main:app --reload` — Start the engine manually for debugging.
- `pytest` — Run the test suite.

---

## How to update
To get the latest engine updates and AI models, run this command in the main project folder:
```bash
git pull
```

---

## How it works
This engine is "Local-First." We use tools like **Whisper** (for text), **Spacy** (for finding names), and **Sentence-Transformers** (for semantic search).

If you want to add a new AI feature, you should:
1. Create a new "Worker" in `app/services/`.
2. Add a "Step" in the `app/pipelines/processing.py` file.
3. Create a "Door" (Route) in `app/api/routes.py`.