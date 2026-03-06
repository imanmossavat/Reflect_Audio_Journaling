from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from enum import Enum
import httpx
import json

import build_prompt

app = FastAPI(title="Journal Reflection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral"

JOURNAL_PATH = "uploaded_journal.txt"

class Mode(str, Enum):
    clarifying = "clarifying"
    deep_dive = "deep_dive"

class Step_N(int, Enum):
    description = 1
    feelings = 2
    evaluation = 3
    analysis = 4
    conclusion = 5
    action = 6

class GenerateRequest(BaseModel):
    mode: Mode  # "clarifying" or "deep_dive"
    step: Step_N | None = None
    topic: str | None = None  # optional focus topic for deep dive
    
@app.post("/upload")
async def upload_journal(file: UploadFile = File(...)):
    content = await file.read()
    text = content.decode("utf-8")
    with open(JOURNAL_PATH, "w") as f:
        f.write(text)
    return {"word_count": len(text.split()), "filename": file.filename}

@app.post("/generate-question")
async def generate_question(req: GenerateRequest):
    try:
        with open(JOURNAL_PATH) as f:
            journal_text = f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No journal uploaded yet.")

    if not journal_text:
        raise HTTPException(status_code=404, detail="Session not found. Please upload your journal again.")

    try:
        prompt = build_prompt.build_prompt(journal_text, req.mode, req.topic, req.step)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    print(f"Prompt length: {len(prompt)} chars")

    async def stream_ollama():
        async with httpx.AsyncClient(timeout = httpx.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0)) as client:
            async with client.stream(
                "POST",
                OLLAMA_URL,
                json={"model": MODEL, "prompt": prompt, "stream": True},
            ) as response:
                if response.status_code != 200:
                    yield f"data: Error contacting Ollama (status {response.status_code})\n\n"
                    return
                async for line in response.aiter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            token = chunk.get("response", "")
                            if token:
                                yield f"data: {json.dumps({'token': token})}\n\n"
                            if chunk.get("done"):
                                yield "data: [DONE]\n\n"
                        except json.JSONDecodeError:
                            continue

    return StreamingResponse(stream_ollama(), media_type="text/event-stream")

@app.get("/ollama-health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get("http://localhost:11434/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
            mistral_ready = any("mistral" in m for m in models)
            return {"status": "ok", "ollama": "reachable", "mistral_available": mistral_ready, "models": models}
    except Exception as e:
        return {"status": "ok", "ollama": "unreachable", "error": str(e)}

