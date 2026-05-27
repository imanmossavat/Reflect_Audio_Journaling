"""Generate the Maya note corpus.

Strategy: events are pre-scripted (not LLM-generated) so we control exactly
which facts exist in the corpus. The LLM only expands each event into a
lived-in, imperfect note in Maya's voice. This guarantees that the gold
supporting notes for the eval's questions actually exist.

Run: python generate_notes.py [--force]
"""
import _bootstrap  # noqa: F401  (sys.path + chroma isolation)

import argparse
import json
import sys
from pathlib import Path

import ollama

from app.services.settings_service import get_setting

HERE = Path(__file__).resolve().parent
NOTES_PATH = HERE / "notes.json"

EVENTS = [
    {
        "note_id": "N-7811",
        "timestamp": "2026-05-12T22:14:00",
        "story_arc_id": "ARC_PROMOTION",
        "summary": "Lina pinged about the promotion evidence Notion doc again. Maya opened it for about 5 minutes, felt confused about which page she's been editing vs. which she abandoned in 2024, closed the laptop without writing anything new.",
        "entities": ["Lina Mourad"],
        "tags": ["promotion", "Notion", "avoidance"],
    },
    {
        "note_id": "N-7812",
        "timestamp": "2026-05-13T09:22:00",
        "story_arc_id": "ARC_APARTMENT",
        "summary": "Karel emailed asking about humidity readings again. Maya thinks they already sent something but maybe it was only photos. Tom says he handled it but Maya can't find a record. The shared Google Drive has three folders called 'final_final' which is not helpful.",
        "entities": ["Karel", "Tom Janssen"],
        "tags": ["mold", "landlord", "documentation"],
    },
    {
        "note_id": "N-7813",
        "timestamp": "2026-05-14T20:05:00",
        "story_arc_id": "ARC_CREATIVE",
        "summary": "Late chat with Yuki about a print shop idea, again. Maya hasn't actually drawn anything in weeks but watched two productivity videos about morning routines for artists.",
        "entities": ["Yuki"],
        "tags": ["illustration", "Discord", "late night"],
    },
    {
        "note_id": "N-7814",
        "timestamp": "2026-05-17T08:41:00",
        "story_arc_id": "ARC_HEALTH",
        "summary": "Did maybe 2 minutes of physio exercises before getting distracted by phone. Bram would probably call that 'not counting'. Maya notices she keeps restarting the routine like it's new every time.",
        "entities": ["Bram"],
        "tags": ["physio", "distraction", "habits"],
    },
    {
        "note_id": "N-7815",
        "timestamp": "2026-05-19T23:48:00",
        "story_arc_id": "ARC_PROMOTION",
        "summary": "Tried to reply to Lina. Wrote a draft, deleted it because it sounded too defensive. Wrote another, deleted it because it sounded weirdly formal. Left the message unsent, told herself she'd send something in the morning when her brain is less whatever this is.",
        "entities": ["Lina Mourad"],
        "tags": ["communication", "tone", "avoidance", "drafts"],
    },
    {
        "note_id": "N-7816",
        "timestamp": "2026-05-20T18:30:00",
        "story_arc_id": "ARC_FAMILY",
        "summary": "Agreed to help Eva cover part of a bill again. Split the amount mentally but didn't write it down anywhere. Tom was working in the other room, Maya didn't mention it yet — doesn't want to explain it badly again.",
        "entities": ["Eva de Vries", "Tom Janssen"],
        "tags": ["money", "Eva", "hidden", "household"],
    },
    {
        "note_id": "N-7817",
        "timestamp": "2026-05-21T11:02:00",
        "story_arc_id": "ARC_HEALTH",
        "summary": "Nora's clinic reminder again. Not clear if it's about the cavity follow-up or the night guard. Nora probably sent something earlier too but Maya can't find it. Inbox has too many unread labels, left it for later.",
        "entities": ["Nora"],
        "tags": ["dentist", "inbox", "admin"],
    },
    {
        "note_id": "N-7818",
        "timestamp": "2026-05-22T21:17:00",
        "story_arc_id": "ARC_APARTMENT",
        "summary": "Opened the mortgage spreadsheet, didn't change anything, just adjusted the same cell ranges and re-read old notes. Maya thinks she uses it more like a thinking space than an actual decision tool, which is probably the problem.",
        "entities": [],
        "tags": ["mortgage", "spreadsheet", "rumination"],
    },
    {
        "note_id": "N-7819",
        "timestamp": "2026-05-15T19:55:00",
        "story_arc_id": "ARC_FAMILY",
        "summary": "Sunday call with dad. Maya said she'd come visit next weekend. Pretty sure she said the same thing last call too. Hans didn't react, just changed subject to weather in Breda. Not sure if he's letting it slide or forgetting.",
        "entities": ["Hans de Vries"],
        "tags": ["family", "phone call", "Breda", "visit"],
    },
    {
        "note_id": "N-7820",
        "timestamp": "2026-05-12T07:35:00",
        "story_arc_id": "ARC_HEALTH",
        "summary": "Tuesday swim again skipped. Pool bag is still by the door from last week, unopened.",
        "entities": [],
        "tags": ["swim", "missed routine"],
    },
    {
        "note_id": "N-7821",
        "timestamp": "2026-05-13T20:11:00",
        "story_arc_id": "ARC_HEALTH",
        "summary": "Restarted the sleep tracker, third app this year. Forgot to wear the wristband going to bed. Two melatonin tabs left in the drawer.",
        "entities": [],
        "tags": ["sleep", "tracking"],
    },
    {
        "note_id": "N-7822",
        "timestamp": "2026-05-14T12:48:00",
        "story_arc_id": "ARC_FAMILY",
        "summary": "Eva sent a long voice message about a wedding shoot that may or may not happen. Maya listened to half of it twice while making coffee.",
        "entities": ["Eva de Vries"],
        "tags": ["voice message", "Eva"],
    },
    {
        "note_id": "N-7823",
        "timestamp": "2026-05-16T15:20:00",
        "story_arc_id": "ARC_CREATIVE",
        "summary": "Cleaned the iPad screen. Did not open Procreate.",
        "entities": [],
        "tags": ["illustration", "iPad", "avoidance"],
    },
    {
        "note_id": "N-7824",
        "timestamp": "2026-05-17T13:30:00",
        "story_arc_id": "ARC_FAMILY",
        "summary": "Miso refused dry food again. Switched bowls, he ate from the new one immediately. The vet appointment for shots is the only thing Maya already put on the shared calendar this month.",
        "entities": [],
        "tags": ["Miso", "cat", "vet"],
    },
    {
        "note_id": "N-7825",
        "timestamp": "2026-05-18T22:02:00",
        "story_arc_id": "ARC_PROMOTION",
        "summary": "Saw a post from Mira about burnout recovery. Thought about it for a while. Did not bookmark it.",
        "entities": ["Mira"],
        "tags": ["burnout", "Mira"],
    },
    {
        "note_id": "N-7826",
        "timestamp": "2026-05-20T09:14:00",
        "story_arc_id": "ARC_APARTMENT",
        "summary": "The dehumidifier Tom bought is running about 6 hours a day now. The bedroom corner still smells faintly off after rain.",
        "entities": ["Tom Janssen"],
        "tags": ["mold", "dehumidifier"],
    },
    {
        "note_id": "N-7827",
        "timestamp": "2026-05-21T19:48:00",
        "story_arc_id": "ARC_CREATIVE",
        "summary": "Sophie left a 9-minute voice message from Copenhagen. Maya hasn't listened yet. Has not visited Sophie since the move.",
        "entities": ["Sophie"],
        "tags": ["Sophie", "voice message", "Copenhagen"],
    },
    {
        "note_id": "N-7828",
        "timestamp": "2026-05-22T08:55:00",
        "story_arc_id": "ARC_PROMOTION",
        "summary": "Ruben's old slack handle now says Inactive User. Maya hovers over it sometimes.",
        "entities": ["Ruben"],
        "tags": ["work", "Ruben"],
    },
    {
        "note_id": "N-7829",
        "timestamp": "2026-05-23T11:40:00",
        "story_arc_id": "ARC_APARTMENT",
        "summary": "Borrowed Anika's drill again to redo one of the kitchen shelf anchors. The uneven shelf is still uneven.",
        "entities": ["Anika"],
        "tags": ["kitchen shelves", "Anika", "drill"],
    },
    {
        "note_id": "N-7830",
        "timestamp": "2026-05-24T13:18:00",
        "story_arc_id": "ARC_HEALTH",
        "summary": "Tax reimbursement email draft moved into a new reminder app. That's the third app the same draft has lived in. Tom asked once, Maya said she was on it.",
        "entities": ["Tom Janssen"],
        "tags": ["tax", "draft", "admin"],
    },
    {
        "note_id": "N-7831",
        "timestamp": "2026-05-25T22:30:00",
        "story_arc_id": "ARC_HEALTH",
        "summary": "ADHD intake form open in a tab. Open in a tab for the second time this month. Did not fill anything in.",
        "entities": [],
        "tags": ["ADHD", "intake", "avoidance"],
    },
    {
        "note_id": "N-7832",
        "timestamp": "2026-05-18T07:50:00",
        "story_arc_id": "ARC_FAMILY",
        "summary": "Daan sent a meme about owing money. Pretty sure it was about the Portugal Airbnb deposit, but he didn't actually say so. Maya laughed and didn't reply.",
        "entities": ["Daan Peters"],
        "tags": ["Daan", "money", "Portugal"],
    },
]

NOTE_EXPANSION_PROMPT = """You are converting a structured journal event into a realistic personal note in Maya's voice.

Maya is a 35-year-old senior UX researcher in Eindhoven. She writes notes to herself in a lived-in, imperfect, fragmentary style — like real journal entries, not polished prose. Sometimes incomplete sentences. Sometimes references prior context implicitly. Sometimes a little dry or self-deprecating. Never resolved or wrapped up neatly.

Rules:
- Keep it short (60-150 words).
- First-person, in Maya's voice.
- Do NOT add facts that aren't in the event summary.
- Do NOT add psychological interpretation or causal explanations that aren't in the summary.
- It's fine for the note to feel a bit unfinished.
- No headers, no bullet points. Just the note text.
- Do not invent new people or new dates.

Event to expand:
- date/time: {timestamp}
- summary: {summary}
- people mentioned: {entities}

Write ONLY the note text. No preamble, no quotes around it.
"""


def expand_event(event: dict, model: str, host: str) -> str:
    prompt = NOTE_EXPANSION_PROMPT.format(
        timestamp=event["timestamp"],
        summary=event["summary"],
        entities=", ".join(event["entities"]) if event["entities"] else "(none)",
    )
    client = ollama.Client(host=host)
    response = client.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.7},
    )
    text = response.get("message", {}).get("content", "").strip()
    # Strip surrounding quotes/backticks the model sometimes adds.
    if text.startswith(("'", '"', "`")) and text.endswith(("'", '"', "`")):
        text = text[1:-1].strip()
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="regenerate even if notes.json exists")
    args = parser.parse_args()

    if NOTES_PATH.exists() and not args.force:
        print(f"{NOTES_PATH.name} already exists; pass --force to regenerate.")
        return 0

    model = get_setting("chat_model")
    host = get_setting("ollama_host")
    print(f"Generating {len(EVENTS)} notes with model={model} host={host}")

    notes = []
    for i, event in enumerate(EVENTS, start=1):
        print(f"  [{i:2d}/{len(EVENTS)}] {event['note_id']} ({event['timestamp']})...", flush=True)
        try:
            text = expand_event(event, model, host)
        except Exception as exc:
            print(f"    FAILED: {exc}", file=sys.stderr)
            text = event["summary"]  # fallback to summary text
        notes.append({
            "note_id": event["note_id"],
            "timestamp": event["timestamp"],
            "text": text,
            "entities": event["entities"],
            "tags": event["tags"],
            "story_arc_id": event["story_arc_id"],
        })

    notes.sort(key=lambda n: n["timestamp"])
    NOTES_PATH.write_text(json.dumps(notes, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(notes)} notes to {NOTES_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
