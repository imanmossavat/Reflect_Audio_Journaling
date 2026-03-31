def build_prompt(journal_text: str) -> str:
    return f"""You are a text analysis assistant. A user has shared a personal journal entry.

Your task is to identify 3 to 6 distinct tags described in this journal entry.
A tag is a recurring theme, subject, or emotional thread and does NOT have to be contiguous.
The same tag may appear in multiple places throughout the text.

For each tag return:
- name: a short label (2-5 words, lowercase)
- summary: one sentence describing what this tag captures
- quotes: a list of 1-5 short, EXACT quotes from the journal text related to this tag. Each quote should be a phrase or sentence copied verbatim from the text (5-40 words). These quotes are used for highlighting, so they MUST appear exactly in the original text.

CRITICAL RULES:
- Every quote MUST be an exact substring of the original text (character-for-character match).
- Do not paraphrase or modify quotes in any way.
- Tags can overlap — the same sentence can belong to multiple tags if relevant.
- Return ONLY a valid JSON array. No explanation, no markdown, no backticks.

Example format:
[
  {{"name": "work stress", "summary": "Recurring pressure and deadlines at the workplace.", "quotes": ["the deadline was approaching fast", "I couldn't focus at work"]}},
  {{"name": "family time", "summary": "Moments spent with children and partner.", "quotes": ["we went to the park together", "my daughter asked me why", "dinner with the family"]}}
]

Journal entry:
\"\"\"
{journal_text}
\"\"\"
"""
