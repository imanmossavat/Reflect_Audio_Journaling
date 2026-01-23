# 🧠 REFLECT – The AI Engine (Backend)

This is the "brain" of the project. It uses Artificial Intelligence to listen to your voice and understand what you said.

---

## 📑 Index
1. [Simple Overview](#-simple-overview)
2. [What's inside?](#-whats-inside)
3. [One-Click Setup](#-one-click-setup)
4. [Advanced Setup](#-advanced-setup)
5. [How it works](#-how-it-works)
6. [How to Update](#-how-to-update)

---

## 💡 Simple Overview
You don't need to touch the code in here to use the app. You just need to make sure this "Engine" is running in the background. 

**Wait, what does it actually do?**
1. **Listens:** It takes your recording and turns it into text (Transcription).
2. **Protects:** It looks for things like your name or phone number so you can hide them (PII Detection).
3. **Organizes:** It groups your talk into chapters (Segmentation).
4. **Feels:** It analyzes the tone of your voice (Prosody).

---

## 📂 What's inside?
If you want to explore the files, here is the map:
- **`api/`**: The "Receptionist." This handles the messages coming from the website.
- **`services/`**: The "Specialists." Each file here has one job (like transcribing or searching).
- **`pipelines/`**: The "Assembly Line." This connects the specialists together to process your audio.
- **`data/`**: The "Archive." This is where your recordings are stored (usually created in the root folder).

---

## 🚀 One-Click Setup
If you haven't done so yet, go back to the [Main Folder](../) and run:
- **Windows:** `setup.bat`
- **Mac:** `setup.command`

This will automatically create your virtual environment and install all necessary AI models for the backend.

---

## 🛠️ Advanced Setup
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

---

## 🔄 How to Update
To get the latest engine updates and AI models, run this command in the main project folder:
```bash
git pull
```

---

## ⚙️ How it works
This engine is "Local-First." We use tools like **Whisper** (for text), **Spacy** (for finding names), and **FAISS** (for searching through your history). 

If you want to add a new AI feature, you should:
1. Create a new "Worker" in `app/services/`.
2. Add a "Step" in the `app/pipelines/processing.py` file.
3. Create a "Door" (Route) in `app/api/routes.py`.