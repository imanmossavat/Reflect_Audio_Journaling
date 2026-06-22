"""LLM summary generation for a source/note.

Mirrors the local-Ollama call pattern used by tag extraction. Synchronous so it can
run inside the ingest pipeline's worker thread (`_process_source_sync`) and from the
regenerate route via `asyncio.to_thread`.
"""
import httpx

from app.prompts import summary_prompt
from app.services.settings_service import get_setting

# Keep long entries from blowing the local model's context window.
_MAX_INPUT_CHARS = 8000


def generate_summary(source_text: str) -> str:
    """Return a one-paragraph LLM summary of `source_text` (may be empty on failure)."""
    text = (source_text or "").strip()
    if not text:
        return ""

    host = get_setting("ollama_host").rstrip("/")
    prompt = summary_prompt.build_prompt(text[:_MAX_INPUT_CHARS])

    response = httpx.post(
        f"{host}/api/generate",
        json={
            "model": get_setting("chat_model"),
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": 256, "temperature": 0.0},
            "think": False,
        },
        timeout=httpx.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0),
    )
    response.raise_for_status()
    return response.json().get("response", "").strip()
