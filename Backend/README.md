# REFLECT – AI Audio Journaling Backend

FastAPI backend for an AI-driven journaling, diary, and note-taking application.  
Processes uploaded or recorded audio into transcriptions, topic segments, and PII detections with summarization support and more features to come.

---
# Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
   - [Directory structure](#directory-structure)
   - [Layer Responsibilities](#layer-responsibilities)
3. [Core Features](#core-features-for-now)
4. [Example Processing Flow](#example-processing-flow)
5. [API Endpoints](#api-endpoints)
6. [Frontend Integration](#frontend-integration)
7. [Why this structure?](#why-this-structure)

---
## Overview

This backend serves as the AI engine behind the REFLECT application.  
It receives audio from the frontend (React), processes it through a clean and extensible pipeline, and returns structured text data ready for storage, visualization, or reflection.

# Core flow:

## Architecture

### Directory structure

---
```
app/
├── api/ # FastAPI routes
│ └── routes.py
├── core/ # Configs, global setup, shared dependencies
│ ├── config.py
│ └── deps.py
├── domain/ # Data models & entities (pure logic)
│ └── models.py
├── services/ # Independent feature modules
│ ├── transcription.py
│ ├── segmentation.py
│ ├── pii.py
│ └── storage.py
├── pipelines/ # Combined workflows (e.g. process_uploaded_audio)
│ └── processing.py
└── main.py # FastAPI entrypoint
```
---

### Layer Responsibilities

| Layer | Purpose | Example |
|-------|----------|---------|
| **domain/** | Defines what entities exist in the system | `Recording`, `Transcript`, `Segment`, `PiiFinding` |
| **core/** | Holds shared setup, config, and constants | model paths, directories, environment variables |
| **services/** | Implements one task per manager | `TranscriptionManager`, `SegmentationManager`, `PIIDetector` |
| **pipelines/** | Defines workflows combining multiple services | `process_uploaded_audio()` |
| **api/** | Exposes endpoints (thin controller layer) | `/api/recordings/upload` |

Think of it as:  
`api` (talk) → `pipelines` (how) → `services` (skills) → `domain` (things) → `core` (tools)

---

## Core Features (for now)

| Feature | Description |
|----------|--------------|
| **Audio Upload** | Accepts audio files from the frontend (recorded in React) |
| **Transcription** | Converts speech to text using Whisper or compatible models |
| **Topic Segmentation** | Splits text into meaningful topics or time-bound sections |
| **PII Detection** | Flags sensitive information (names, emails, phones, etc.) |
| **Export / Import (future)** | Move or back up the full library securely |

---

## Example Processing Flow

```python
from app.pipelines.processing import process_uploaded_audio

result = process_uploaded_audio("voice_note.wav", open("voice_note.wav","rb").read())

print(result["transcript"])
print(result["segments"])
print(result["pii"])
```
---

Output example:

```json
{
  "recording_id": "a81c4dfe12ab",
  "transcript": "Today I talked about my new job at Philips...",
  "segments": [
    {"start_s": 0, "end_s": 45, "label": "Morning reflections"},
    {"start_s": 45, "end_s": 120, "label": "Work update"}
  ],
  "pii": [
    {"label": "ORG", "preview": "Philips"},
    {"label": "PERSON", "preview": "Anass"}
  ]
}
```
---
## API Endpoints
| Endpoint                 | Method | Description                                   |
| ------------------------ | ------ | --------------------------------------------- |
| `/api/recordings/upload` | `POST` | Upload audio and run full processing pipeline |
| `/api/transcriptions`    | `POST` | Return only transcript                        |
| `/api/segments`          | `POST` | Return topic segmentation                     |
| `/api/pii`               | `POST` | Return PII detections                         |

Each endpoint accepts multipart/form-data with:

- file: audio file (e.g. .wav, .mp3, .webm)
- language: optional (en default)

## Frontend integration

Recording will happen entirely in the React frontend:
```tsx
const blob = new Blob(chunks, { type: "audio/webm" });
await uploadRecording(blob);
```

---
## Why this structure?
| Benefit        | Explanation                                     |
| -------------- | ----------------------------------------------- |
| **Modular**    | Swap models or add AI features easily           |
| **Readable**   | Each layer has a single responsibility          |
| **Scalable later** | Managers can become separate services if needed |

---