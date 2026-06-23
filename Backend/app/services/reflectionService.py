import json

import httpx

from app.prompts import topic_grouping_prompt
from app.services.settings_service import get_setting


def _call_grouping_llm(prompt: str) -> str:
    """Non-streaming Ollama call for topic grouping. Mirrors tagService extraction."""
    host = get_setting("ollama_host").rstrip("/")
    response = httpx.post(
        f"{host}/api/generate",
        json={
            "model": get_setting("chat_model"),
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": 1024},
            "think": False,
        },
        timeout=httpx.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0),
    )
    response.raise_for_status()
    return response.json().get("response", "").strip()


def _parse_grouping_response(raw: str) -> list[dict]:
    json_start = raw.find("[")
    json_end = raw.rfind("]") + 1
    if json_start == -1 or json_end <= json_start:
        raise ValueError("No JSON array found in topic grouping response")
    data = json.loads(raw[json_start:json_end])
    topics: list[dict] = []
    for item in data:
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        items = [str(q).strip() for q in (item.get("items", []) or []) if str(q).strip()]
        topics.append({
            "name": name,
            "summary": str(item.get("summary", "")).strip(),
            "items": items,
        })
    return topics


def group_topics(journal_text: str) -> list[dict]:
    """Group a journal bundle into 2-5 named topics, each with supporting excerpts.

    Lets the user pick a single theme to reflect on without naming it themselves.
    """
    if not (journal_text or "").strip():
        return []
    prompt = topic_grouping_prompt.build_prompt(journal_text)
    raw = _call_grouping_llm(prompt)
    return _parse_grouping_response(raw)
