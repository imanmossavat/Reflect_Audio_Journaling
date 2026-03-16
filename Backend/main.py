from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi import Response
from pydantic import BaseModel
from enum import Enum
import httpx
import json
import ollama

import question_prompt
import dictionary_question_prompt
import simpler_dictionary_question_prompt
import topic_prompt

app = FastAPI(title="Journal Reflection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], #frontend server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3.5:4b"

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

class Topic(BaseModel):
    name: str
    summary: str
    quotes: list[str]

class GenerateRequest(BaseModel):
    mode: Mode  # "clarifying" or "deep_dive"
    step: Step_N | None = None
    topic: str | None = None  # topic name for deep dive focus
    topic_summary: str | None = None  # topic summary for context
    history: list[dict] | None = None  # Q&A history with timestamps
    
@app.post("/upload")
async def upload_journal(file: UploadFile = File(...)):
    content = await file.read()
    text = content.decode("utf-8")
    with open(JOURNAL_PATH, "w") as f:
        f.write(text)
    return {"word_count": len(text.split()), "filename": file.filename}

class TopicResponse(BaseModel):
    topics: list[Topic]
    journal_text: str

@app.get("/journal-text")
async def get_journal_text():
    try:
        with open(JOURNAL_PATH) as f:
            journal_text = f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No journal uploaded yet.")
    if not journal_text:
        raise HTTPException(status_code=404, detail="Journal is empty.")
    return {"journal_text": journal_text}

@app.post("/topics")
async def extract_topics() -> TopicResponse:
    try:
        with open(JOURNAL_PATH) as f:
            journal_text = f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No journal uploaded yet.")

    if not journal_text:
        raise HTTPException(status_code=404, detail="Journal is empty.")

    prompt = topic_prompt.build_prompt(journal_text)

    try:
        async with httpx.AsyncClient(timeout = httpx.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0)) as client:
            response = await client.post(
                OLLAMA_URL,
                json={"model": MODEL, "prompt": prompt, "stream": False, "options": {"num_predict": 1024}, "think": False},
            )
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Ollama error")

            result = response.json()
            response_text = result.get("response", "").strip()

            try:
                json_start = response_text.find('[')
                json_end = response_text.rfind(']') + 1
                if json_start == -1 or json_end <= json_start:
                    raise ValueError("No JSON array found in response")

                json_str = response_text[json_start:json_end]
                raw_topics = json.loads(json_str)

                topics: list[Topic] = []
                for t in raw_topics:
                    topics.append(Topic(
                        name=t.get("name", ""),
                        summary=t.get("summary", ""),
                        quotes=t.get("quotes", []),
                    ))

                return TopicResponse(topics=topics, journal_text=journal_text)
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                print(f"Parse error: {str(e)}")
                print(f"Response text: {response_text}")
                raise HTTPException(status_code=500, detail=f"Failed to parse topics: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Topic extraction error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Topic extraction failed: {str(e)}")

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
        messages = simpler_dictionary_question_prompt.build_messages(
            journal_text,
            mode=req.mode,
            topic=req.topic,
            topic_summary=req.topic_summary,
            step=req.step,
            history=req.history,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    print(f"Messages count: {len(messages)}")
    for msg in messages:
        print(f"  [{msg['role']}]: {msg['content']}")

    async def stream_ollama():
        try:
            stream = ollama.chat(model=MODEL, messages=messages, stream=True, think=False)
            for chunk in stream:
                token = chunk.get("message", {}).get("content", "")
                if token:
                    yield f"data: {json.dumps({'token': token})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'token': f'Error: {str(e)}'})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(stream_ollama(), media_type="text/event-stream")

@app.get("/ollama-health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get("http://localhost:11434")
            return Response(
                content=r.content,
                status_code=r.status_code,
                media_type=r.headers.get("content-type", "text/plain"),
            )
    except Exception as e:
        return {"status": "ok", "ollama": "unreachable", "error": str(e)}

