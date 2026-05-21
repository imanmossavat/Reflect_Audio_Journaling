import json
import re
import httpx


def suggest_tags_via_llm(source_text: str) -> list[dict]:
    prompt = _build_prompt(source_text)
    raw = _call_llm(prompt)
    return _parse_response(raw)


#Prompt

_SYSTEM_PROMPT = """You are a neutral tagging assistant for a reflective source app.
Your only job is to suggest short keyword tags that describe the key themes in the source.

Rules:
- Suggest between 3 and 8 tags.
- Tags must be single words or short phrases (max 3 words), all lowercase.
- Never interpret emotions, assign importance, or draw conclusions.
- Only surface themes that are clearly present in the text.
- For each tag provide a brief, factual reason (one sentence, max 15 words).
- Respond ONLY with a JSON array. No preamble, no markdown fences.

Format:
[
  {"name": "tag-name", "reason": "Factual one-sentence reason."},
  ...
]"""


def _build_prompt(source_text: str) -> str:
    # Truncate to avoid blowing the context window on very long sources
    truncated = source_text[:4000]
    return f"Source entry:\n\n{truncated}"



def _call_llm(user_prompt: str) -> str:
    from app.services.settings_service import get_setting
    host = get_setting("ollama_host").rstrip("/")

    response = httpx.post(
        f"{host}/api/chat",
        json={
            "model": get_setting("chat_model"),
            "stream": False,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
        },
        timeout=httpx.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0),
    )
    response.raise_for_status()
    return response.json()["message"]["content"]



def _parse_response(raw: str) -> list[dict]:
    # Strip accidental markdown fences the model might add despite instructions
    cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()

    try:
        data = json.loads(cleaned)
        if not isinstance(data, list):
            return []
        return [
            {
                "name": str(item.get("name", "")).strip().lower(),
                "reason": str(item.get("reason", "")).strip(),
            }
            for item in data
            if item.get("name")
        ]
    except (json.JSONDecodeError, TypeError):
        # If parsing fails entirely, return empty so the UI can handle it
        return []