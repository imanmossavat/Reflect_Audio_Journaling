from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from enum import Enum
import httpx
import json
import re

import question_prompt
import segment_prompt

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

class Segment(BaseModel):
    name: str
    summary: str
    startIndex: int
    endIndex: int

class GenerateRequest(BaseModel):
    mode: Mode  # "clarifying" or "deep_dive"
    step: Step_N | None = None
    topic: str | None = None  # optional focus topic for deep dive
    history: list[dict] | None = None  # Q&A history with timestamps
    segment: str | None = None  # focused segment text
    segment_indexes: tuple[int, int] | None = None  # (startIndex, endIndex) of the segment
    
@app.post("/upload")
async def upload_journal(file: UploadFile = File(...)):
    content = await file.read()
    text = content.decode("utf-8")
    with open(JOURNAL_PATH, "w") as f:
        f.write(text)
    return {"word_count": len(text.split()), "filename": file.filename}

@app.post("/segment")
async def segment_journal() -> list[Segment]:
    try:
        with open(JOURNAL_PATH) as f:
            journal_text = f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No journal uploaded yet.")

    if not journal_text:
        raise HTTPException(status_code=404, detail="Journal is empty.")

    prompt = segment_prompt.build_prompt(journal_text)

    try:
        async with httpx.AsyncClient(timeout = httpx.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0)) as client:
            response = await client.post(
                OLLAMA_URL,
                json={"model": MODEL, "prompt": prompt, "stream": False},
            )
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Ollama error")

            result = response.json()
            response_text = result.get("response", "").strip()

            # Parse JSON response
            try:
                # Try to extract JSON from the response (in case there's extra text)
                json_start = response_text.find('[')
                json_end = response_text.rfind(']') + 1
                if json_start == -1 or json_end <= json_start:
                    raise ValueError("No JSON array found in response")

                json_str = response_text[json_start:json_end]
                raw_segments = json.loads(json_str)

                # Convert to Segment objects with correct field names
                segments: list[Segment] = []
                for seg in raw_segments:
                    segments.append(Segment(
                        name=seg.get("name", ""),
                        summary=seg.get("summary", ""),
                        startIndex=seg.get("start", 0),
                        endIndex=seg.get("end", 0)
                    ))

                return segments
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                print(f"Parse error: {str(e)}")
                print(f"Response text: {response_text}")
                raise HTTPException(status_code=500, detail=f"Failed to parse segments: {str(e)}")
    except Exception as e:
        print(f"Segment error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Segmentation failed: {str(e)}")

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
        prompt = question_prompt.build_prompt(
            journal_text,
            mode=req.mode,
            topic=req.topic,
            step=req.step,
            history=req.history,
            segment_text=req.segment,
            segment_indexes=req.segment_indexes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    print(f"Prompt length: {len(prompt)} chars")
    print(f"Prompt :{prompt}")

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

