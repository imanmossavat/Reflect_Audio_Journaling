def build_prompt(journal_text: str) -> str:
    text_length = len(journal_text)
    return f"""You are a text analysis assistant. A user has shared a personal journal entry.

Your task is to split this journal entry into 3 to 6 thematic segments.
A segment is a contiguous block of sentences that share a common theme, event, or emotional thread.

For each segment return:
- name: a short label (2-5 words, lowercase, no underscores)
- summary: one sentence describing what this segment is about
- startIndex: character index where this segment begins in the original text
- endIndex: character index where this segment ends in the original text

CRITICAL RULES:
- The first segment MUST start at index 0.
- The last segment MUST end at index {text_length}.
- Each segment's startIndex MUST equal the previous segment's endIndex (no gaps, no overlaps).
- Together, all segments must cover every single character of the text.
- The total character count of the journal is exactly {text_length}.
- Return ONLY a valid JSON array. No explanation, no markdown, no backticks.
- Do not segment a word in half. Segments should ideally end at natural sentence boundaries like ".", but if necessary, they can split sentences as long as they follow the above rules and do not split words.

Example format (for a text of 891 characters with 3 segments):
[
  {{"name": "example topic", "summary": "...", "startIndex": 0, "endIndex": 300}},
  {{"name": "another topic", "summary": "...", "startIndex": 300, "endIndex": 600}},
  {{"name": "final topic", "summary": "...", "startIndex": 600, "endIndex": 891}}
]

Journal entry ({text_length} characters):
\"\"\"
{journal_text}
\"\"\"
"""