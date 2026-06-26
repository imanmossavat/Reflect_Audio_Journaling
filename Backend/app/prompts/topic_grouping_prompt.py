# JSON Schema passed to Ollama's `format` parameter so the output is grammar-constrained
# to a valid topic array — the structure below is enforced by the decoder, not requested.
RESPONSE_FORMAT = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "summary": {"type": "string"},
            "items": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["name", "summary", "items"],
    },
}


def build_prompt(journal_text: str) -> str:
    return f"""You are a neutral organiser for a reflective journaling app. A user has selected one or more stream-of-thought journal sources and wants to reflect on a single theme.

Your only job is to group the statements in the journal into distinct topics, so the user can pick which one to reflect on. Do not interpret, do not label emotions, do not assign importance, and do not suggest actions. Only surface themes that are clearly present in the text, described in the user's own terms.

Rules:
- Identify between 2 and 5 distinct topics.
- Each topic has a short, neutral name (max 5 words) and a brief factual summary (one sentence, max 20 words).
- For each topic, list 2 to 4 "items": short, near-verbatim excerpts from the journal that belong to that topic. Keep them faithful to the user's wording.

Each topic is an object with "name", "summary", and an "items" list of excerpts, for example:
[
  {{"name": "topic name", "summary": "Factual one-sentence summary.", "items": ["short excerpt", "short excerpt"]}}
]

Journal:
\"\"\"
{journal_text}
\"\"\"
"""
