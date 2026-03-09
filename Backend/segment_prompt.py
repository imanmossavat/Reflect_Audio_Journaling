def build_prompt(journal_text: str) -> str:
    return f"""You are a text analysis assistant. A user has shared a personal journal entry.

Your task is to identify between 3 and 6 distinct thematic segments in this journal entry.
A segment is a coherent set of sentences that share a common theme, event, or emotional thread.

For each segment return:
- name: a short label (2-5 words, lowercase)
- summary: one sentence describing what this segment is about
- start: character index where this segment begins in the original text
- end: character index where this segment ends in the original text

Rules:
- Segments must be contiguous and cover the entire text with no gaps
- Do not overlap segments
- Do not invent content that is not in the journal
- Return only valid JSON, no explanation, no markdown, no backticks

Return format:
[
  {{"name": "...", "summary": "...", "start": 0, "end": 412}},
  {{"name": "...", "summary": "...", "start": 412, "end": 891}}
]

Journal entry:
\"\"\"
{journal_text}
\"\"\"
"""