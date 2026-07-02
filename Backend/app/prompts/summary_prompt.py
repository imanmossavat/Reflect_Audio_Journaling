# Bump when the wording below changes so derived_meta records which version produced
# a stored summary (lets a later pass recompute only stale summaries).
SUMMARY_PROMPT_VERSION = "v2"


def build_prompt(journal_text: str) -> str:
    return f"""You are a neutral summarisation assistant for a personal journal app.

Write a concise summary of the journal entry below.

Rules:
- One short paragraph, 1-3 sentences, max ~60 words.
- Factual and neutral: describe what the entry is about. Do NOT interpret emotions,
  judge, advise, or add anything not present in the text.
- Write in the third person ("The entry describes...").
- The entry's author writes in first person ("I"). When converting to third person,
  refer to the author as "the writer" — never by the name of anyone the author merely
  mentions in the text. Names that appear inside the entry refer to other people,
  distinct from the author, unless the entry says otherwise.
- Respond with the summary text only — no preamble, no markdown, no quotes.

Journal entry:
\"\"\"
{journal_text}
\"\"\"
"""
