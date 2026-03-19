def build_messages(journal_text: str, mode: str, topic: str | None = None, topic_summary: str | None = None, step: int | None = None, history: list[dict] | None = None) -> list[dict]:

    common_rules = """
Rules:
- Ask exactly one question.
- Use the word "you".
- Refer to a phrase or idea from the journal.
- One sentence only.
- Output only the question.
"""

    if mode == "clarifying":
        system_content = f"""
You ask reflective questions about a journal entry.

Task:
Ask ONE open-ended question that helps the user reflect deeper.
    """ + common_rules

    elif mode == "deep_dive":
        step_questions = {
            1: "Ask about a concrete moment or situation mentioned in the journal.",
            2: "Ask about what the user experienced or felt in that moment.",
            3: "Ask what worked well and what felt difficult.",
            4: "Ask what patterns or conditions they notice.",
            5: "Ask what insights they are starting to see.",
            6: "Ask what they might want to explore or try next.",
        }

        step_instruction = step_questions.get(step, step_questions[1])

        system_content = f"""
You ask reflective questions using the Gibbs reflection cycle.

Current step:
{step_instruction}
    """ + common_rules

    else:
        raise ValueError(f"Unknown mode: {mode}")

    messages = [
        {"role": "system", "content": system_content}
    ]

    user_content = f"""
Journal entry:

{journal_text}
"""

    if topic:
        user_content += f"\nFocus topic: {topic}"

    messages.append({"role": "user", "content": user_content})

    # Optional: keep only the last 2 Q&A pairs to reduce context load
    if history:
        for entry in history[-2:]:
            if entry.get("question"):
                messages.append({"role": "assistant", "content": entry["question"]})
            if entry.get("answer"):
                messages.append({"role": "user", "content": entry["answer"]})

    return messages