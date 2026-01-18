import os
import json
import random
import subprocess
import re
from typing import List, Dict
from faker import Faker

from personas.personas_config import PERSONAS

fake = Faker()
random.seed(42)

OUTPUT_ROOT = "synthetic_persona_data_v5"
NUM_ENTRIES_PER_PERSONA = 30
LLM_MODEL = "llama3.2:3b"


# --------------------------------------------------------
# LLM CALL — SIMPLE, STABLE, NO JSON, NO FORMATTING COMPLEXITY
# --------------------------------------------------------

def call_llm(prompt: str) -> str:
    """Call Ollama and return raw text."""
    result = subprocess.run(
        ["ollama", "run", LLM_MODEL],
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore"
    )
    return result.stdout.strip()


# --------------------------------------------------------
# PII GENERATION + DETECTION
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
        "home_address": fake.address().replace("\n", ", ")
    }


def find_pii_offsets(transcript: str, pii_bank: Dict) -> List[Dict]:
    labels = []
    for key, value in pii_bank.items():
        start = 0
        while True:
            idx = transcript.find(value, start)
            if idx == -1:
                break
            labels.append({
                "type": key.upper(),
                "text": value,
                "start_char": idx,
                "end_char": idx + len(value)
            })
            start = idx + len(value)
    return labels


# --------------------------------------------------------
# ARC + MEMORY
# --------------------------------------------------------

def choose_arc_stage(persona: Dict, idx: int) -> str:
    stages = persona["arc_stages"]
    stage_idx = int(idx / max(1, NUM_ENTRIES_PER_PERSONA - 1) * (len(stages) - 1))
    return stages[stage_idx]


def build_memory_summary(prev_entries: List[Dict]) -> str:
    if not prev_entries:
        return "No previous entries."
    last = prev_entries[-3:]
    snippets = [e["transcript"].split(".")[0][:200] for e in last]
    return " | ".join(snippets)


# --------------------------------------------------------
# STEP 1 — RAW JOURNAL ENTRY (LLM)
# --------------------------------------------------------

def generate_raw_entry(persona: Dict, pii_bank: Dict,
                       idx: int, previous_entries: List[Dict]) -> str:

    arc_stage = choose_arc_stage(persona, idx)
    memory_summary = build_memory_summary(previous_entries)

    n_topics = random.randint(1, min(3, len(persona["core_themes"])))
    todays_topics = random.sample(persona["core_themes"], n_topics)

    prompt = f"""
Write a personal journal entry of 8–18 sentences for the following persona.

Persona:
Name: {persona["name"]} (do NOT use full name)
Age: {persona["age"]}
Background: {persona["background"]}
Neurotype: {persona["neurotype"]}

Style guidelines:
{persona["style_instructions"]}

Life arc today:
{arc_stage}

Recent memory:
{memory_summary}

Main themes today:
{", ".join(todays_topics)}

PII you MAY reference:
romantic partner: {pii_bank["partner_name"]}
close friend: {pii_bank["close_friend"]}
mother: {pii_bank["mother_name"]}
mentor: {pii_bank["mentor_name"]}
boss: {pii_bank["boss_name"]}
company: {pii_bank["company_name"]}
city: {pii_bank["city"]}
email: {pii_bank["email"]}
phone: {pii_bank["phone"]}
address: {pii_bank["home_address"]}

Rules:
- Write a natural, emotional, reflective journal entry.
- DO NOT output lists or JSON.
- DO NOT break immersion.
"""

    return call_llm(prompt)


# --------------------------------------------------------
# STEP 2 — SENTENCE SPLITTING
# --------------------------------------------------------

def split_into_sentences(text: str) -> List[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


# --------------------------------------------------------
# STEP 3 — PER-SENTENCE TOPIC CLASSIFICATION
# --------------------------------------------------------

ALLOWED_TOPICS = [
    "relationships", "school", "work", "internship", "anxiety",
    "health", "identity", "family", "self-worth",
    "social-interaction", "emotions", "goals"
]

def classify_topic(sentence: str) -> str:
    prompt = f"""
Classify the topic of this sentence into EXACTLY ONE of:
{", ".join(ALLOWED_TOPICS)}

Sentence:
"{sentence}"

Output ONLY the topic word.
"""
    raw = call_llm(prompt).lower().strip()

    if raw not in ALLOWED_TOPICS:
        return "general"
    return raw


def classify_topics(sentences: List[str]) -> List[str]:
    return [classify_topic(s) for s in sentences]


# --------------------------------------------------------
# STEP 4 — GROUP SENTENCES INTO SEGMENTS
# --------------------------------------------------------

def build_segments(sentences: List[str], topics: List[str]) -> List[Dict]:
    segments = []
    curr_topic = topics[0]
    curr_group = []

    for sent, top in zip(sentences, topics):
        if top == curr_topic:
            curr_group.append(sent)
        else:
            segments.append({"topic": curr_topic,
                             "text": " ".join(curr_group)})
            curr_topic = top
            curr_group = [sent]

    segments.append({"topic": curr_topic,
                     "text": " ".join(curr_group)})

    # collapse 1-topic entries
    if len(set(topics)) == 1:
        return [segments[0]]

    # cap to 4 segments
    return segments[:4]


# --------------------------------------------------------
# STEP 5 — SENTIMENT PER SEGMENT (EACH SEPARATE)
# --------------------------------------------------------

def classify_sentiment(text: str) -> str:
    prompt = f"""
Classify the sentiment of this text as EXACTLY ONE of:
positive, neutral, negative

Text:
"{text}"

Output ONLY the sentiment word.
"""
    raw = call_llm(prompt).lower().strip()
    return raw if raw in ["positive", "neutral", "negative"] else "neutral"


def label_segment_sentiments(segments: List[Dict]) -> List[str]:
    return [classify_sentiment(seg["text"]) for seg in segments]


# --------------------------------------------------------
# STEP 6 — BUILD FINAL ENTRY
# --------------------------------------------------------

def stitch_segments(segments: List[Dict], sentiments: List[str]):
    transcript = ""
    stitched = []

    for i, seg in enumerate(segments):
        txt = seg["text"].strip()
        if not txt.endswith("."):
            txt += "."

        if transcript:
            transcript += " "

        start = len(transcript)
        transcript += txt
        end = len(transcript)

        stitched.append({
            "id": i,
            "topic": seg["topic"],
            "sentiment": sentiments[i],
            "text": txt,
            "start_char": start,
            "end_char": end
        })

    return transcript, stitched


def build_entry(persona: Dict, pii_bank: Dict,
                idx: int, previous_entries: List[Dict]) -> Dict:

    raw = generate_raw_entry(persona, pii_bank, idx, previous_entries)
    sentences = split_into_sentences(raw)
    topics = classify_topics(sentences)
    segments = build_segments(sentences, topics)
    sentiments = label_segment_sentiments(segments)

    transcript, stitched_segments = stitch_segments(segments, sentiments)
    pii_labels = find_pii_offsets(transcript, pii_bank)
    summary = call_llm(f"Summarize this in 1–2 sentences:\n{transcript}")

    return {
        "transcript": transcript,
        "segments": stitched_segments,
        "topics": list({seg["topic"] for seg in stitched_segments}),
        "pii": pii_labels,
        "summary": summary,
        "arc_stage": choose_arc_stage(persona, idx)
    }


# --------------------------------------------------------
# MAIN
# --------------------------------------------------------

def generate_dataset():
    os.makedirs(OUTPUT_ROOT, exist_ok=True)

    for persona in PERSONAS:
        out_dir = os.path.join(OUTPUT_ROOT, f"{persona['id']:02d}_{persona['code']}")
        os.makedirs(out_dir, exist_ok=True)

        pii_bank = build_pii_bank(persona)
        prev_entries = []

        for i in range(NUM_ENTRIES_PER_PERSONA):
            entry = build_entry(persona, pii_bank, i, prev_entries)

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
                }
            }

            with open(os.path.join(out_dir, f"entry_{i:03d}.json"),
                      "w", encoding="utf-8") as f:
                json.dump(record, f, indent=2, ensure_ascii=False)

            prev_entries.append(entry)
            print(f"[{persona['code']}] Entry {i} done")


if __name__ == "__main__":
    generate_dataset()
