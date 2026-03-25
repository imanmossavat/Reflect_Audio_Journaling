import ollama
import json
from typing import List


def llm_split_journal(text: str) -> List[str]:
    prompt = f"""Your task is to split a journal into individual entries or segments.

Rules:
- If you see day labels (Monday, Tuesday, Next Monday, etc.) ALWAYS split on them, each day is its own segment.
- If no day labels exist, split where the topic, mood, or time clearly shifts
- Every segment must be a separate element in the array

Return ONLY a raw JSON array of strings. Example format:
["segment one text", "segment two text", "segment three text"]

Journal:
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


def chunk_text(text: str, journal_id: int) -> List[dict]:
    if not text or not text.strip():
        return []

    try:
        segments = llm_split_journal(text)
    except Exception:
        # Keep processing alive if LLM chunking fails.
        segments = [text.strip()]

    if not segments:
        # Prevent silent success with no chunks.
        segments = [text.strip()]

    return [
        {"text": segment, "journal_id": str(journal_id)}
        for segment in segments
        if segment
    ]