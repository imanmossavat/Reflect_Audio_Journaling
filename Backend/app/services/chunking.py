import ollama
import json
import re
import spacy

from typing import List

nlp = spacy.load("en_core_web_sm")

def llm_split_source(text: str) -> List[str]:
    prompt = f"""Your task is to split a source into individual entries or segments.

Rules:
- If you see day labels (Monday, Tuesday, Next Monday, etc.) ALWAYS split on them, each day is its own segment.
- If no day labels exist, split where the theme, mood, or time clearly shifts
- Every segment must be a separate element in the array

Return ONLY a raw JSON array of strings. Example format:
["segment one text", "segment two text", "segment three text"]

Source:
{text}
"""
    response = ollama.chat(
        model="mistral",
        messages=[{"role": "user", "content": prompt}],
        format="json",
    )

    content = response.get("message", {}).get("content", "")
    if not content:
        raise ValueError("LLM chunking returned an empty message.")

    try:
        segments = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM chunking returned invalid JSON: {content[:200]}") from exc

    if isinstance(segments, dict):
        values = list(segments.values())
        segments = values[0] if values else []

    if not isinstance(segments, list):
        raise ValueError("LLM chunking output was not a list.")

    cleaned = [str(s).strip() for s in segments if str(s).strip()]
    return cleaned


def split_on_days(text: str):
    #^ → start of line only , (?im) → multiline + case insensitive , \b → whole word match , [:\-\n\s] → expects structure after it
    pattern = r"(?im)^(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b[:\-\n\s]"
    parts = re.split(pattern, text, flags=re.IGNORECASE)

    if len(parts) <= 1:
        return None  # no structure found

    segments = []
    for i in range(1, len(parts), 2):
        day = parts[i]
        content = parts[i + 1] if i + 1 < len(parts) else ""
        segments.append(f"{day} {content}".strip())

    return segments


def sentence_chunk(text: str):
    doc = nlp(text)
    sentences = [s.text.strip() for s in doc.sents if s.text.strip()]

    chunks = []
    current = ""

    for s in sentences:
        if len(current) + len(s) < 500:
            current += " " + s
        else:
            chunks.append(current.strip())
            current = s

    if current:
        chunks.append(current.strip())

    return chunks


def chunk_text(text: str, source_id: int):
    if not text or not text.strip():
        return []

    # 1. Try day-based split (cheap + strong)
    segments = split_on_days(text)

    # 2. If no structure → sentence chunking
    if not segments:
        print("no segments from regex")
        segments = sentence_chunk(text)

    print("check")
    print(segments)

    # 3. If there is still only 1 chunk and it's very long → try LLM split (expensive)
    if len(segments) == 1 and len(segments[0]) > 1000:
        try:
            segments = llm_split_source(text)
        except Exception:
            pass  # keep previous result

    return [
        {"text": segment, "source_id": source_id}
        for segment in segments if segment
    ]