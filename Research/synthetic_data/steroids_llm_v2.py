import os
import json
import random
import subprocess
from typing import List, Dict

from personas.personas_config import PERSONAS
from faker import Faker

fake = Faker()
random.seed(42)

OUTPUT_ROOT = "synthetic_persona_data_v8"
NUM_ENTRIES_PER_PERSONA = 30
LLM_MODEL = "llama3.2:3b"

# Probability an entry gets an explicit intro segment
DEFAULT_INTRO_PROB = 0.7

# Phrases we absolutely do NOT want
BANNED_OPENERS = [
    "as i sit here",
    "as i lay here",
    "as i'm sitting",
]
BANNED_PHRASES = [
    "as i sit here",
    "as i lay here",
    "as i'm sitting",
]


# --------------------------------------------------------
# LLM util
# --------------------------------------------------------

def call_llm(prompt: str) -> str:
    """Simple wrapper for calling Ollama."""
    result = subprocess.run(
        ["ollama", "run", LLM_MODEL],
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    return result.stdout.strip()


# --------------------------------------------------------
# PII generation and offsets
# --------------------------------------------------------

def build_pii_bank(persona: Dict) -> Dict:
    return {
        "partner_name": fake.name(),
        "mother_name": fake.name(),
        "father_name": fake.name(),
        "close_friend": fake.name(),
        "mentor_name": fake.name(),
        "boss_name": fake.name(),
        "company_name": fake.company(),
        "city": fake.city(),
        "email": fake.email(),
        "phone": fake.phone_number(),
        "home_address": fake.address().replace("\n", ", "),
    }


def find_pii_offsets(text: str, pii_bank: Dict) -> List[Dict]:
    labels = []
    for key, value in pii_bank.items():
        start = 0
        while True:
            idx = text.find(value, start)
            if idx == -1:
                break
            labels.append(
                {
                    "type": key.upper(),
                    "text": value,
                    "start_char": idx,
                    "end_char": idx + len(value),
                }
            )
            start = idx + len(value)
    return labels


# --------------------------------------------------------
# Arc + memory
# --------------------------------------------------------

def choose_arc_stage(persona: Dict, i: int) -> str:
    stages = persona["arc_stages"]
    stage_index = int(i / max(1, NUM_ENTRIES_PER_PERSONA - 1) * (len(stages) - 1))
    return stages[stage_index]


def build_memory_summary(previous_entries: List[Dict]) -> str:
    if not previous_entries:
        return "No previous entries yet."
    snippets = [e["transcript"].split(".")[0][:200] for e in previous_entries[-3:]]
    return " | ".join(snippets)


# --------------------------------------------------------
# Sentiment classification
# --------------------------------------------------------

def classify_sentiment(text: str) -> str:
    prompt = f"""
Classify the sentiment of the following journal text as EXACTLY ONE of:
positive, neutral, negative

Text:
"{text}"

Output ONLY the sentiment word.
"""
    out = call_llm(prompt).lower().strip()
    if out not in ["positive", "neutral", "negative"]:
        return "neutral"
    return out


# --------------------------------------------------------
# Intro generation (optional segment)
# --------------------------------------------------------

def generate_intro(
    persona: Dict,
    pii_bank: Dict,
    entry_index: int,
    previous_entries: List[Dict],
    todays_topics: List[str],
) -> str:
    arc_stage = choose_arc_stage(persona, entry_index)
    memory_summary = build_memory_summary(previous_entries)

    banned_openers_str = ", ".join(f'"{b}"' for b in BANNED_OPENERS)
    banned_phrases_str = ", ".join(f'"{b}"' for b in BANNED_PHRASES)

    prompt = f"""
Write the INTRO of a personal journal entry (3–6 sentences) for this persona.

Persona:
Name: {persona["name"]} (do NOT use full name)
Age: {persona["age"]}
Background: {persona["background"]}
Neurotype: {persona["neurotype"]}

Style:
{persona["style_instructions"]}

Life arc today:
{arc_stage}

Recent memory:
{memory_summary}

Main themes that will appear later:
{", ".join(todays_topics)}

PII you MAY mention if natural:
partner: {pii_bank["partner_name"]}
friend: {pii_bank["close_friend"]}
mentor: {pii_bank["mentor_name"]}
boss: {pii_bank["boss_name"]}
company: {pii_bank["company_name"]}

Rules:
- Write as if the person is reflecting on how today feels overall.
- DO NOT list options.
- DO NOT explain the writing.
- DO NOT describe transitions.
- DO NOT use bullet points or numbering.
- DO NOT use any of the following phrases anywhere: {banned_phrases_str}.
- DO NOT start any sentence with: {banned_openers_str}.
- Vary sentence openings; avoid repeating the exact same opening pattern.
"""

    return call_llm(prompt).strip()


# --------------------------------------------------------
# Topic-focused segment generation
# --------------------------------------------------------

def generate_topic_segment(
    persona: Dict,
    pii_bank: Dict,
    entry_index: int,
    previous_entries: List[Dict],
    intro_text: str,
    todays_topics: List[str],
    topic: str,
) -> str:
    arc_stage = choose_arc_stage(persona, entry_index)
    memory_summary = build_memory_summary(previous_entries)

    banned_openers_str = ", ".join(f'"{b}"' for b in BANNED_OPENERS)
    banned_phrases_str = ", ".join(f'"{b}"' for b in BANNED_PHRASES)

    prompt = f"""
Continue the journal entry naturally, shifting focus toward this topic:
"{topic}"

Persona:
Name: {persona["name"]}
Neurotype: {persona["neurotype"]}

Life arc today:
{arc_stage}

Recent memory:
{memory_summary}

Intro already written today:
{intro_text}

Other topics for today:
{", ".join(todays_topics)}

Write 4–7 sentences.

Rules:
- Stay consistent with the intro, but focus mainly on this topic.
- You may refer to emotions, worries, specific events, sensory details, etc.
- DO NOT list options.
- DO NOT explain what you are doing.
- DO NOT use words like "this segment" or "this topic".
- DO NOT describe transitions.
- DO NOT use bullet points or numbering.
- DO NOT use any of the following phrases anywhere: {banned_phrases_str}.
- DO NOT start any sentence with: {banned_openers_str}.
- Avoid repeating the exact same sentence starter you used earlier in this entry.
- Write as if the persona is just continuing their own private journal.
"""

    return call_llm(prompt).strip()


# --------------------------------------------------------
# Stitch segments into transcript
# --------------------------------------------------------

def stitch_segments(segments_raw: List[Dict]):
    transcript = ""
    stitched = []

    for i, seg in enumerate(segments_raw):
        text = seg["text"].strip()
        if not text.endswith("."):
            text += "."

        if transcript:
            transcript += " "

        start = len(transcript)
        transcript += text
        end = len(transcript)

        stitched.append(
            {
                "id": i,
                "topic": seg["topic"],
                "sentiment": seg["sentiment"],
                "text": text,
                "start_char": start,
                "end_char": end,
            }
        )

    return transcript, stitched


# --------------------------------------------------------
# Build full entry
# --------------------------------------------------------

def build_entry(
    persona: Dict,
    pii_bank: Dict,
    entry_index: int,
    previous_entries: List[Dict],
) -> Dict:
    # choose 1–3 topics for the day
    n_topics = random.randint(1, min(3, len(persona["core_themes"])))
    todays_topics = random.sample(persona["core_themes"], n_topics)

    # decide whether this entry uses an explicit intro segment
    intro_prob = float(persona.get("intro_probability", DEFAULT_INTRO_PROB))
    use_intro = random.random() < intro_prob

    segments_raw: List[Dict] = []
    intro_text = ""

    if use_intro:
        intro_text = generate_intro(
            persona, pii_bank, entry_index, previous_entries, todays_topics
        )
        segments_raw.append(
            {
                "topic": "general",
                "text": intro_text,
            }
        )
    else:
        # intro is just empty string for context; segments will still be coherent
        intro_text = ""

    # topic segments
    for topic in todays_topics:
        seg_text = generate_topic_segment(
            persona, pii_bank, entry_index, previous_entries, intro_text, todays_topics, topic
        )
        segments_raw.append(
            {
                "topic": topic,
                "text": seg_text,
            }
        )

    # sentiment per segment (including intro if present)
    for seg in segments_raw:
        seg["sentiment"] = classify_sentiment(seg["text"])

    # stitch into transcript
    transcript, stitched_segments = stitch_segments(segments_raw)

    # pii labels
    pii_labels = find_pii_offsets(transcript, pii_bank)

    # summary
    summary_prompt = f"""
Summarize this journal entry in 1–2 sentences, capturing both what happened and how the person feels:

{transcript}
"""
    summary = call_llm(summary_prompt).strip()

    return {
        "transcript": transcript,
        "segments": stitched_segments,
        "topics": [seg["topic"] for seg in segments_raw if seg["topic"] != "general"],
        "pii": pii_labels,
        "summary": summary,
        "arc_stage": choose_arc_stage(persona, entry_index),
    }


# --------------------------------------------------------
# Main loop
# --------------------------------------------------------

def generate_dataset():
    os.makedirs(OUTPUT_ROOT, exist_ok=True)

    for persona in PERSONAS:
        persona_dir = os.path.join(
            OUTPUT_ROOT, f"{persona['id']:02d}_{persona['code']}"
        )
        os.makedirs(persona_dir, exist_ok=True)

        pii_bank = build_pii_bank(persona)
        previous_entries: List[Dict] = []

        for i in range(NUM_ENTRIES_PER_PERSONA):
            entry = build_entry(persona, pii_bank, i, previous_entries)

            record = {
                "persona": persona["code"],
                "entry_index": i,
                "arc_stage": entry["arc_stage"],
                "transcript": entry["transcript"],
                "segments": entry["segments"],
                "topics": entry["topics"],
                "pii": entry["pii"],
                "summary": entry["summary"],
                "persona_metadata": {
                    "name": persona["name"],
                    "age": persona["age"],
                    "neurotype": persona["neurotype"],
                },
            }

            path = os.path.join(persona_dir, f"entry_{i:03d}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)

            previous_entries.append(entry)
            print(f"[{persona['code']}] entry {i} done")


if __name__ == "__main__":
    generate_dataset()
