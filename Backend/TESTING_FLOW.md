# Backend Testing Flow (Step-by-Step)

## File Placement
Place this file in:
- Backend/TESTING_FLOW.md

Reason:
- It is backend-only test guidance.
- It sits next to backend setup files (environment.yml, alembic.ini).
- Teacher can run everything from the Backend folder without searching elsewhere.

---

## 1. Start Required Services

1. Open terminal 1:
```bash
ollama serve
```

2. Pull required models (once):
```bash
ollama pull qwen3.5:4b
ollama pull mistral
ollama pull nomic-embed-text
ollama pull llama3
```

3. Open terminal 2:
```bash
cd Backend
conda activate REFLECT
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

4. Open Swagger:
- http://localhost:8000/docs

---

## 2. Main Happy Path (Single Upload Type)
Use only one upload path: processed text file upload.

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
- Use the `journal.id` from upload.

4. POST `/generate-question`
- Body example:
```json
{
  "mode": "clarifying",
  "step": 1,
  "focus_tag": null,
  "focus_tag_summary": null,
  "history": []
}
```
- Copy the generated question text from stream output.

5. POST `/save-answer`
- Important flow rule: save only after you have a generated question.
- Use the generated question text and your answer.
- Body:
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
- Uses journal text and suggests tags.

2. POST `/journals/{journal_id}/tags/suggest/confirm`
- Body:
```json
{
  "names": ["stress", "planning"]
}
```

3. GET `/journals/search?tags=stress,planning&match=any`
- Confirms tag-based retrieval works.

---

## 4. Mobile Upload Over HTTP (Current Temporary Setup)

1. Run backend with host binding enabled:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

2. Put phone and laptop on the same Wi-Fi.

3. Find laptop IPv4 (Windows):
```bash
ipconfig
```

4. On phone browser open:
- `http://<LAPTOP_IPV4>:8000/docs`

5. Test POST `/journal/uploadFile/processed` from phone with `.txt` file.

6. Verify upload result by checking returned `journal.id` and then calling:
- GET `/journal/{journal_id}`

Notes:
- This is plain HTTP for local-network testing only.
- No HTTPS/TLS expected in this stage.

---

## 5. Quick Error Checks

1. Upload unsupported extension to `/journal/uploadFile/processed`.
- Expect HTTP 400.

2. POST `/query` with empty question.
- Expect HTTP 400.

3. Tag endpoint with unknown journal id.
- Expect HTTP 404.
