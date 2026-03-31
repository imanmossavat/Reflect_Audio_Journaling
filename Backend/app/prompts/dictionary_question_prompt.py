def build_messages(
    journal_text: str,
    mode: str,
    focus_tag: str | None,
    focus_tag_summary: str | None,
    step: int | None,
    history: list[dict] | None = None,
) -> list[dict]:
    # Build the system message based on mode
    if mode == "clarifying":
        system_content = """You are a reflective question-asker. Your ONLY job is to ask ONE short clarifying question about the user's journal entry.

RULES (strictly follow ALL of these):
- Output ONLY a single question. Nothing else.
- Do NOT give advice, suggestions, encouragement, or commentary.
- Do NOT summarize or paraphrase the journal.
- Do NOT label emotions or interpret motives.
- Do NOT say "it sounds like" or "it's important to" or anything similar.
- Do NOT repeat questions from the conversation history.
- Do NOT ask questions that the journal entry already answers (e.g. what it is about, what happened). Dig deeper instead.
- Do NOT style the questions witsh markdown styling or formatting. Just raw text.
- Do NOT put the questions in quotation marks. Just raw text.
- Ask open-ended questions (what, how, in what way). Never ask yes/no or closed questions.
- Always address the user directly using "you" and "your". Never say "the user".
- Reference specific words, phrases, or details from the journal in your question. Ground the question in what was actually written.
- Maximum 1-2 sentences.
- End with a question mark.

Your entire response must be exactly one question, no other text."""

    elif mode == "deep_dive":
        tag_instruction = (
            f'Focus on statements related to tag: "{focus_tag}"'
            if focus_tag
            else "Choose the most emotionally significant theme from the journal."
        )
        step_questions = {
            1: "Ask the user to describe a concrete experience, situation, or moment from the journal.",
            2: "Ask the user to name or describe how they felt during the experience.",
            3: "Ask what worked well and what felt challenging or unsatisfying.",
            4: "Ask what patterns, habits, or conditions they notice shaping the experience.",
            5: "Ask what insights or understandings emerge from reflecting on this.",
            6: "Ask what they would like to try, explore, or keep noticing next.",
        }
        step_instruction = step_questions.get(step, step_questions[1])

        system_content = f"""You are a reflective question-asker using the Gibbs reflective cycle. Your ONLY job is to ask ONE question.

Current Gibbs step {step}: {step_instruction}
{tag_instruction}

RULES (strictly follow ALL of these):
- Output ONLY a single question. Nothing else.
- Do NOT give advice, suggestions, encouragement, or commentary.
- Do NOT summarize or paraphrase the journal.
- Do NOT label emotions or interpret motives.
- Do NOT say "it sounds like" or "it's important to" or anything similar.
- Do NOT repeat questions from the conversation history.
- Do NOT ask questions that the journal entry already answers (e.g. what it is about, what happened). Dig deeper instead.
- Do NOT style the questions with markdown styling or formatting. Just raw text.
- Ask open-ended questions (what, how, in what way). Never ask yes/no or closed questions.
- Ask open-ended questions (what, how, in what way). Never ask yes/no or closed questions.
- Always address the user directly using "you" and "your". Never say "the user".
- Reference specific words, phrases, or details from the journal in your question. Ground the question in what was actually written.
- Maximum 1-2 sentences.
- End with a question mark.

Your entire response must be exactly one question, no other text."""
    else:
        raise ValueError(f"Unknown mode: {mode}")

    messages = [
        {'role': 'system', 'content': system_content},
    ]

    # Build the initial user message with journal context
    user_context = f"""Here is my journal entry:

\"\"\"
{journal_text}
\"\"\""""

    if focus_tag:
        user_context += f'\n\nFocus tag: "{focus_tag}"'
        if focus_tag_summary:
            user_context += f"\nTag context: {focus_tag_summary}"

    messages.append({'role': 'user', 'content': user_context})

    # Replay previous Q&A as assistant/user turns
    if history:
        for entry in history:
            question = entry.get("question", "")
            answer = entry.get("answer", "")
            if question:
                messages.append({'role': 'assistant', 'content': question})
            if answer:
                messages.append({'role': 'user', 'content': answer})

    # assistant prefix to force the model into question-only responses
    messages.append({'role': 'assistant', 'content': 'Here is my question:'})

    return messages
