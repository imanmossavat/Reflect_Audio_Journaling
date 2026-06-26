import json

import httpx

from app.prompts import topic_grouping_prompt
from app.services.settings_service import chat_num_ctx, get_setting


def _call_grouping_llm(prompt: str) -> str:
    """Non-streaming Ollama call for topic grouping. Mirrors tagService extraction."""
    host = get_setting("ollama_host").rstrip("/")
    response = httpx.post(
        f"{host}/api/generate",
        json={
            "model": get_setting("chat_model"),
            "prompt": prompt,
            "stream": False,
            "format": topic_grouping_prompt.RESPONSE_FORMAT,
            # num predict is way higher than the expected output size
            "options": {"num_ctx": chat_num_ctx(), "num_predict": 4096, "temperature": 0},
            "think": False,
        },
        timeout=httpx.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0),
    )
    response.raise_for_status()
    data = response.json()
    if data.get("done_reason") == "length":
        raise ValueError("topic grouping output truncated (hit num_predict/num_ctx)")
    return data.get("response", "").strip()


def _parse_grouping_response(raw: str) -> list[dict]:
    # `format` guarantees a valid JSON array conforming to the schema, so parse directly.
    data = json.loads(raw)
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
