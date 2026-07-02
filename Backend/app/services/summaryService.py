import httpx

from app.prompts import summary_prompt
from app.services.llm_runtime import model_supports_thinking
from app.services.settings_service import chat_num_ctx, get_setting
from app.utils.strip_thinking import strip_thinking

# Keep long entries from blowing the local model's context window.
_MAX_INPUT_CHARS = 8000


def generate_summary(source_text: str) -> str:
    """Return a one-paragraph LLM summary of `source_text` (may be empty on failure)."""
    text = (source_text or "").strip()
    if not text:
        return ""

    host = get_setting("ollama_host").rstrip("/")
    chat_model = get_setting("chat_model")
    prompt = summary_prompt.build_prompt(text[:_MAX_INPUT_CHARS])

    # /api/chat, not /api/generate — the same endpoint generation_registry.py's RAG path
    # uses, where a reasoning model's <think> block reliably lands in the response's
    # separate `message.thinking` field instead of leaking inline into `message.content`.
    # Only send `think` when the model actually has the capability (mirrors
    # generation_registry.py's model_supports_thinking gate); summaries never want
    # visible reasoning, so when it's supported it's explicitly turned off.
    payload = {
        "model": chat_model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"num_ctx": chat_num_ctx(), "num_predict": 512, "temperature": 0.0},
    }
    if model_supports_thinking(chat_model):
        payload["think"] = False

    response = httpx.post(
        f"{host}/api/chat",
        json=payload,
        timeout=httpx.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0),
    )
    response.raise_for_status()
    content = response.json().get("message", {}).get("content", "")
    # Defensive backstop: strip a leaked <think>...</think> block even if the `think`
    # flag above wasn't honored for this model/Ollama version.
    return strip_thinking(content).strip()
