# 🎙️ REFLECT – Your Private AI Audio Journal

Welcome! REFLECT is a private, local tool for recording your thoughts and getting AI-powered insights — without your data ever leaving your computer.

---

## 🚀 Getting Started

You'll need **two terminals** open — one for the backend, one for the frontend.

---

## 1. Backend Setup

```bash
cd Backend
```

### Create & activate the Conda environment

```bash
conda env create -f requirements.txt
conda activate reflect
```

> If you don't have Conda, install it from [conda.io](https://docs.conda.io/en/latest/miniconda.html)

### Run the backend

```bash
python app.py
```

The backend will start on `http://localhost:5000`

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