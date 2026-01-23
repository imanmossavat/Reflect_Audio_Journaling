# 🎙️ REFLECT – Your Private AI Audio Journal

Welcome! **REFLECT** is a private, local tool for recording your thoughts and getting AI-powered insights without your data ever leaving your computer.

---

## 📑 Table of Contents
1. [What is REFLECT?](#-what-is-reflect)
2. [🚀 One-Click Setup](#-one-click-setup)
3. [⚡ Quick Start Guide (Daily Use)](#-quick-start-guide-daily-use)
4. [🔄 Updating & Maintenance](#-updating--maintenance)
5. [📂 Project Layout](#-project-layout)

---

## 🌟 What is REFLECT?
Most AI tools send your voice to a server in the cloud. **REFLECT is different.** 
- **Private:** Processes everything on your own machine.
- **Transcribes:** Turns your voice into text automatically.
- **Analyzes:** Finds "PII" (private info), splits talk into topics, and checks mood/tone.
- **Searchable:** Search your journals by meaning, not just exact words.

---

## 🚀 One-Click Setup
If you just downloaded the project, follow these two steps:

1.  **Install Requirements:** Download and install [Python (3.10.11)](https://www.python.org/downloads/release/python-31011/) and [Node.js](https://nodejs.org/).
2.  **Run the Setup:**
    - **Windows:** Double-click `setup.bat`
    - **Mac:** Double-click `setup.command`

*This will automatically create your virtual environment, install all AI models, and set up the website design tools.*

---

## ⚡ Quick Start Guide (Daily Use)
Once setup is complete, you can start the entire system every day with one click:

1.  **Windows:** Double-click `start_engine.bat`
2.  **Mac:** Double-click `start_engine.command`

**What happens next?**
- The AI Engine starts.
- The Website starts.
- **Your browser opens automatically** to `http://localhost:3000`.

---

## 🔄 Updating & Maintenance
To get new features or fixes, open a terminal in this main folder and run:
```bash
git pull
```
*Note: If new dependencies are added, simply run the **Setup** file again.*

---

## 📂 Project Layout
- **[Backend](./Backend):** The **Engine**. This is where the AI lives.
- **[Frontend](./Frontend):** The **Dashboard**. This is what you see and click on.
- **[Research](./Research):** The **Architect's Blueprints**. Tests and notes from development.
- **[data/](./data):** The **Archive**. Where your journals are saved.

---

## ❓ Troubleshooting
- **"Command not found":** Restart your computer after installing Python and Node.js.
- **Engine Offline:** Ensure the terminal window opened by `start_engine` is still running.
- **Setup Failed:** Ensure you have an active internet connection to download the AI models.

---
**Technical details?** See [Backend README](./Backend/README.md) or [Frontend README](./Frontend/README.md).