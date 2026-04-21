# 🎙️ REFLECT – Your Private AI Audio Journal

Welcome! REFLECT is a private, local tool for recording your thoughts and getting AI-powered insights — without your data ever leaving your computer.

---

## 📋 Prerequisites

### 1. Install Ollama

REFLECT uses a local AI model via Ollama.

1. Download and install Ollama: https://ollama.com
2. Open a terminal and pull the required models:

```bash
ollama pull gemma4:e4b
ollama pull nomic-embed-text
```

Keep Ollama running in the background while using REFLECT.

### 2. Install Miniconda

REFLECT uses Conda to manage Python dependencies.

1. Download Miniconda from: https://docs.conda.io/en/latest/miniconda.html
2. Run the installer and follow the setup wizard
3. **Important**: When prompted, check the box to **"Add Miniconda3 to my PATH"** (even though it says not recommended)
4. Complete the installation
5. Open **Anaconda Prompt** (search for it in your Start menu)
6. Verify the installation by running:
   ```bash
   conda --version
   ```

---

## 🚀 Getting Started – First Time Setup

You'll need **two terminals** open — one for the backend, one for the frontend.

---

## 1. Backend Setup (Terminal 1)

### Step 1: Navigate to the Backend folder

```bash
cd Backend
```

### Step 2: Initialize Conda

```bash
conda init
```

Then **close and reopen your terminal** for changes to take effect.

### Step 3: Create the Conda environment

```bash
conda create -f environment.yml
```

This creates a new environment with all required dependencies.

### Step 4: Activate the environment

```bash
conda activate REFLECT
```

You should see `(REFLECT)` at the start of your terminal prompt.

### Step 5: Create the local database

```bash
alembic upgrade head
```

### Step 6: Run the backend

```bash
python start_backend.py
```

The backend will start on `http://localhost:8000`

The terminal will remain active and show logs. **Keep this terminal open.**

---

## 2. Frontend Setup (Terminal 2)

Open a **second terminal** (not the same one as the backend), then:

### Step 1: Navigate to the Frontend folder

```bash
cd Frontend
```

### Step 2: Verify Next.js configuration

Open `next.config.mjs` and ensure the backend IP is correctly configured:

```javascript
// next.config.mjs
const config = {
  // Make sure this points to your backend
  // Usually: http://localhost:8000 (for local development)
};
```

If you're running the backend on a different IP, update it accordingly.

### Step 3: Install dependencies

```bash
npm install
```

### Step 4: Run the frontend

```bash
npm run dev
```

The app will be available at `http://localhost:3000`

The terminal will remain active and show logs. **Keep this terminal open.**

---

## ✅ You're All Set!

Open your browser and go to **http://localhost:3000**

Both terminals need to stay open while using the app.

---

## 🔄 Restarting After Setup

If you close the terminals and want to run REFLECT again:

### Backend (Terminal 1):
```bash
cd Backend
conda activate REFLECT
python start_backend.py
```

### Frontend (Terminal 2):
```bash
cd Frontend
npm run dev
```

No need to reinstall or recreate the environment — just activate and run!