import json
import re
import httpx

from sqlmodel import Session

from app.db import engine
from app.prompts import tag_extraction_prompt
from app.repositories import tagRepository
from database.models import Source


def extract_and_store_tags(
    source_id: int, *, origin: str = "llm", replace_existing: bool = True
) -> tuple[list[dict], str]:
    """Extract themed tags from a source's text via the LLM and persist them.

    Reused by the `/extract-tags` route and the ingest enrichment step. Synchronous so it
    runs in the pipeline worker thread (and via `asyncio.to_thread` from the async route).

    When `replace_existing` is set, only the source's `origin="llm"` tag links are cleared
    first, so a recompute refreshes auto-tags while preserving the user's manual tags.

    Returns ``(tags, source_text)`` where each tag is ``{name, summary, quotes}``.
    """
    with Session(engine) as session:
        source = session.get(Source, source_id)
        if not source:
            raise ValueError(f"Source {source_id} not found")
        source_text = source.text or ""
    if not source_text.strip():
        raise ValueError(f"Source {source_id} has no text to tag")

    raw = _call_extraction_llm(tag_extraction_prompt.build_prompt(source_text))
    tags = _parse_extraction_response(raw)

    with Session(engine) as session:
        if replace_existing:
            tagRepository.clear_llm_tags_for_source(session, source_id, commit=False)
        for tag_item in tags:
            normalised = str(tag_item.get("name", "")).strip().lower()
            if not normalised:
                continue
            tag = tagRepository.get_or_create_tag(session, name=normalised)
            tagRepository.add_tag_to_source(
                session, source_id=source_id, tag_id=tag.id, origin=origin, commit=False
            )
        session.commit()

    return tags, source_text


def _call_extraction_llm(prompt: str) -> str:
    from app.services.settings_service import chat_num_ctx, get_setting
    from app.services.llm_runtime import model_supports_thinking
    from app.utils.strip_thinking import strip_thinking

    host = get_setting("ollama_host").rstrip("/")
    chat_model = get_setting("chat_model")
    # /api/chat, not /api/generate — see summaryService.generate_summary for why: a
    # reasoning model's <think> block reliably lands in the separate `message.thinking`
    # field here instead of leaking inline into `message.content`. `think` is only sent
    # when the model has the capability (mirrors generation_registry.py's
    # model_supports_thinking gate); extraction never wants visible reasoning.
    payload = {
        "model": chat_model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        # Grammar-constrain the output to a valid tag array (Ollama structured outputs).
        "format": tag_extraction_prompt.RESPONSE_FORMAT,
        # num_predict is a finite circuit breaker far above the schema's worst case
        # (~900 tokens) — only a degenerate loop hits it, surfaced by the check below.
        "options": {"num_ctx": chat_num_ctx(), "num_predict": 4096, "temperature": 0},
    }
    if model_supports_thinking(chat_model):
        payload["think"] = False
    response = httpx.post(
        f"{host}/api/chat",
        json=payload,
        timeout=httpx.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0),
    )
    response.raise_for_status()
    data = response.json()
    if data.get("done_reason") == "length":
        raise ValueError("tag extraction output truncated (hit num_predict/num_ctx)")
    content = data.get("message", {}).get("content", "")
    # Defensive backstop: strip a leaked <think>...</think> block even if the `think`
    # flag above wasn't honored for this model/Ollama version.
    return strip_thinking(content).strip()


def _parse_extraction_response(raw: str) -> list[dict]:
    # `format` guarantees a valid JSON array conforming to the schema, so parse directly.
    data = json.loads(raw)
    return [
        {
            "name": str(item.get("name", "")).strip(),
            "summary": str(item.get("summary", "")).strip(),
            "quotes": list(item.get("quotes", []) or []),
        }
        for item in data
        if item.get("name")
    ]


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
    from app.services.settings_service import chat_num_ctx, get_setting
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
            # Same shared window so this call doesn't trigger a model reload.
            "options": {"num_ctx": chat_num_ctx()},
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