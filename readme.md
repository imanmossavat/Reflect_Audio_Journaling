# REFLECT — Local-First AI Audio Journaling

<p align="center">
  <strong>Privacy-first speech journaling with AI-assisted reflection</strong><br/>
  Built for applied research at Fontys
</p>

<p align="center">
  <img src="https://img.shields.io/badge/status-active%20research-blue" />
  <img src="https://img.shields.io/badge/privacy-local--first-green" />
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey" />
</p>

---

## Overview

**REFLECT** is a local-first AI journaling tool that transforms spoken input into structured, searchable, and meaningful reflections.

The system is designed to:

* Lower the barrier to reflection using speech
* Support structured thinking without being intrusive
* Keep all personal data on-device

This project is part of applied research exploring how AI can assist reflective practices while maintaining **user autonomy and ethical boundaries**.

---

## Features

* Speech-to-text transcription
* Personal data (PII) detection
* Prosody analysis (tone, emotion cues)
* Topic segmentation and labeling
* Semantic search across journal entries
* Optional local LLM integration (RAG-based reflection)

---

## Architecture Pipeline

The REFLECT pipeline processes raw audio into structured insights:

1. Record or upload audio
2. Transcribe speech to text
3. Detect personal identifiers (PII)
4. Analyze prosody
5. Segment and label topics
6. Store and enable semantic retrieval
7. (Prototype) Generate reflections via local LLM (RAG)

<p align="center">
  <img src="basic-functionality/Images/Algorithmic%20pipeline.png" width="800"/>
</p>

---

## Quickstart

### Recommended Setup (basic-functionality)

```bash
cd basic-functionality
```

#### Run setup script

* Windows:

```bash
setup.bat
```

* macOS:

```bash
./setup.command
```

* Linux:

```bash
./setup.sh
```

#### Start the system

* Windows:

```bash
start_engine.bat
```

* macOS:

```bash
./start_engine.command
```

* Linux:

```bash
./start_engine.sh
```

### Documentation

* Backend: `basic-functionality/Backend/README.md`
* Frontend: `basic-functionality/Frontend/README.md`

---

## RAG Prototype (LLM Reflection)

For advanced reflection capabilities using Retrieval-Augmented Generation:

```bash
cd RAG-solution
```

See:

* `RAG-solution/README.md`
* `RAG-solution/Backend/README.md`

---

## Repository Structure

```
.
├── basic-functionality   # Stable end-to-end demo
├── RAG-solution          # LLM + RAG prototype
├── Research              # Experiments, notebooks, papers
```

---

## Design Principles

### Privacy First

* All journal data remains local
* No cloud dependency by default

### Human-Centered AI

* AI assists reflection, not decision-making
* No authoritative or prescriptive outputs

### Modularity

* Components can be used independently
* Supports experimentation and research workflows

---

## Status

This repository contains:

* Stable demo component (`basic-functionality`)
* Experimental prototype (`RAG-solution`)
* Research artifacts

Expect ongoing changes and iteration.

---

## Future Work

* Improved reflection prompting strategies with local LLM's
* Better emotion/prosody modeling
* UI/UX improvements for journaling flow
* Mobile uploading integration

---

## Acknowledgements

Developed as part of applied research at **Fontys University of Applied Sciences**.
