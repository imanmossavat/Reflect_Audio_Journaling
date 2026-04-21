# Backend Testing Flow (Step-by-Step)
## 1. Start Required Services

1. Open terminal 1 — start Ollama:
```bash
ollama serve
```

2. Pull required models (once):
```bash
ollama pull qwen3.5:4b
ollama pull mistral
ollama pull nomic-embed-text
ollama pull llama3
ollama pull gpt-oss:20b
ollama pull gemma:e4b
```

3. Open terminal 2 — start backend:
```bash
cd Backend
conda activate REFLECT
alembic upgrade head
python start_backend.py
```

This prints your local and network URLs, opens a QR code for phone access, and starts the server.

4. Open Swagger on desktop:
- http://localhost:8000/docs

Or scan the QR code to open Swagger on your phone.

---

## 2. Main Happy Path

1. POST `/journal/uploadFile/processed`
- Upload one `.txt` file.
- Save returned `journal.id`.

2. POST `/query`
- Body:
```json
{
  "question": "What are the main themes in this journal?",
  "top_k": 5
}
```

3. POST `/extract-tags?journal_id={journal_id}`

4. POST `/generate-question`
```json
{
  "mode": "clarifying",
  "step": 1,
  "focus_tag": null,
  "focus_tag_summary": null,
  "history": []
}
```
- Copy the generated question text from the stream output.

5. POST `/save-answer`
```json
{
  "journal_id": 1,
  "question_text": "<paste generated question>",
  "answer_text": "<your answer>"
}
```

---

## 3. Tag Flow

1. GET `/journals/{journal_id}/tags/suggest`

2. POST `/journals/{journal_id}/tags/suggest/confirm`
```json
{
  "names": ["stress", "planning"]
}
```

3. GET `/journals/search?tags=stress,planning&match=any`

---

## 4. Mobile Upload Over HTTP

Phone and laptop must be on the same Wi-Fi. The network URL and QR code are printed automatically when you run `start_backend.py`.

1. Scan the QR code or open the printed network URL on your phone.
2. POST `/journal/uploadFile/raw` from phone with any eligible file.
3. Verify with GET `/journal/{journal_id}` using the returned id.

> Plain HTTP for local-network testing only. No HTTPS/TLS at this stage.