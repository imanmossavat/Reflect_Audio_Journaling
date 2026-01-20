# REFLECT – AI Audio Journaling System

REFLECT is a local-first, privacy-aware AI audio journaling system.
It allows users to record or upload audio, transcribe it, analyze it,
and reflect on patterns over time while keeping data under user control.

This repository contains both the **working application** and the
**research and evaluation work** that informed its design.

---

# Installation steps

## Environment Setup (macOS & Windows)

Follow these steps to set up a local Python environment for the REFLECT backend.

---
### Prerequisites
- Python 3.10.11
- `pip` (comes with Python)
- Git
- Anaconda / miniconda (optional, for conda users)
  
Download links:
- Python 3.10.11: https://www.python.org/downloads/release/python-31011/
- Git: https://git-scm.com/downloads
- Miniconda: https://docs.conda.io/en/latest/miniconda.html
- Anaconda: https://www.anaconda.com/products/distribution

Check your versions:
```bash
python --version
pip --version
git --version
```

### Clone the repository
Clone the repo from git and go into the backend directory. Choose which folder you want to clone it into, right click and open command prompt inside that folder.
```bash
git clone https://github.com/imanmossavat/Reflect_Audio_Journaling.git
cd Reflect_Audio_Journaling
cd Backend
```
Make sure you stay in the 'backend' folder for the remaining steps.

### Create a virtual environment

#### Windows

###### Command Prompt (CMD)
```bash
py -3.10 -m venv .venv
.venv\Scripts\Activate
```

###### PowerShell
```bash
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

#### macOS/Linux
```bash
python3.10 -m venv .venv
source .venv/bin/activate
```

### Alternative: Using conda
This is an **alternative setup**. The remaining steps (installing dependencies
and running the backend) are the same as in the standard installation.
If you prefer using `conda`, create and activate the environment with:
```bash
conda create -n reflect python=3.10.11
conda activate reflect
```

## Installation
Depending on your WIFI and computer speed this may take long, it has not frozen, longer waiting times is expected.
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Starting the application
Run the command below and wait for application startup to finish, Once running, the API documentation is available at http://localhost:8000/docs:
```bash
uvicorn app.main:app --reload
```

## Using the application
Then visit http://localhost:8000/docs, it is possible that you already have something running on port 8000,
in that case you can specify another port with the `--port` flag, e.g. `--port 8001`. Or just let the application choose its own port.
In that case wait for the application to start up and copy the URL from the terminal.

Once you have done this you can use the interactive API documentation to try out the endpoints.
![img.png](Installation/Images/img.png)
---
You can do so by clicking on the endpoint you want to try out, then click on the "Try it out" button. It also tells you what parameters it expects, so for this endpoint you need to provide text in the request body.
![img_1.png](Installation/Images/img_1.png)
---
After you click on try it out you can provide the text you want to analyze, then click on the "Execute" button.
![img_2.png](Installation/Images/img_2.png)
---
Then the response will appear below with the analyzed text.
![img_3.png](Installation/Images/img_3.png)
---

- Project: REFLECT – AI Audio Journaling System

---