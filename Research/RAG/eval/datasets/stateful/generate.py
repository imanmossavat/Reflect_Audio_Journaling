"""Generate the STATEFUL (Niels) note corpus -> datasets/stateful/notes.json.

Harder multi-hop / state-evolution set. Hand-authored structured events are
LLM-expanded into first-person notes. See datasets/stateful/world_state.json for
the hidden answer key, and questions.json for the annotated QA.

Design rules baked into the events:
- One state-transition STEP per note. Never summarize a whole arc in one note.
- No status words in the prose (no "former", "current", "ex", "new job", "now works").
  Status must be INFERABLE from dates + several notes, not read off one note.
- Distractor notes mention prior employers / lost bids / abandoned project so they are
  strong retrieval candidates but insufficient to answer alone.

Run:  python datasets/stateful/generate.py            # LLM-expand via Ollama
      python datasets/stateful/generate.py --raw       # skip the LLM, use summaries verbatim
      python datasets/stateful/generate.py --force      # regenerate over an existing file
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))
import _bootstrap  # noqa: F401,E402

import argparse
import json

import ollama

from app.services.settings_service import get_setting

HERE = Path(__file__).resolve().parent
NOTES_PATH = HERE / "notes.json"

# story_arc_id: ARC_EMPLOYMENT | ARC_RELATIONSHIP | ARC_PROJECT | ARC_RESIDENCE | ARC_NOISE
# state: traceability only (carried into notes.json, ignored by the harness).
EVENTS = [
    {"note_id": "S-001", "timestamp": "2025-09-08T09:12:00", "story_arc_id": "ARC_EMPLOYMENT",
     "summary": "Standup at Meridian Logistics ran twenty minutes over again. Same warehouse-routing tickets I've had since I joined two years ago. Pushed the carrier-rate fix before lunch.",
     "entities": ["Meridian Logistics"], "tags": ["work", "Meridian", "routine"],
     "state": {"var": "employment", "value": "Meridian Logistics", "transition": "context"}},

    {"note_id": "S-002", "timestamp": "2025-09-15T21:40:00", "story_arc_id": "ARC_RELATIONSHIP",
     "summary": "Priya and I finally tried that ramen place by the Markthal. She kept the receipt to remember the name. Good evening.",
     "entities": ["Priya"], "tags": ["Priya", "relationship"],
     "state": {"var": "relationship", "value": "Priya", "transition": "context"}},

    {"note_id": "S-003", "timestamp": "2025-09-20T23:05:00", "story_arc_id": "ARC_PROJECT",
     "summary": "Sketched out an idea tonight - a small self-hosted recipe app, just for me. Calling it Saffron. Wrote the data model on the back of a napkin.",
     "entities": [], "tags": ["Saffron", "side project", "idea"],
     "state": {"var": "side_project", "value": "planned", "transition": "plan"}},

    {"note_id": "S-004", "timestamp": "2025-10-05T18:22:00", "story_arc_id": "ARC_PROJECT",
     "summary": "Saffron has a working first version. I can add a recipe, it saves to SQLite, the list renders. Spent the whole Saturday on it and didn't notice the time.",
     "entities": [], "tags": ["Saffron", "side project", "building"],
     "state": {"var": "side_project", "value": "active", "transition": "activate"}},

    {"note_id": "S-005", "timestamp": "2025-10-19T22:30:00", "story_arc_id": "ARC_NOISE",
     "summary": "Climbing with Joost at the gym on Schiekade. He's stronger than me on overhangs, as usual. Beers after.",
     "entities": ["Joost"], "tags": ["climbing", "Joost"], "state": None},

    {"note_id": "S-006", "timestamp": "2025-11-15T20:10:00", "story_arc_id": "ARC_RELATIONSHIP",
     "summary": "Priya moved the last of her boxes out this weekend. The flat echoes now. We were careful with each other, which somehow made it worse.",
     "entities": ["Priya"], "tags": ["Priya", "breakup"],
     "state": {"var": "relationship", "value": "Priya", "transition": "breakup"}},

    {"note_id": "S-007", "timestamp": "2025-12-10T23:50:00", "story_arc_id": "ARC_PROJECT",
     "summary": "Haven't opened the Saffron repo since November. It just sits there. Couldn't bring myself to touch it this month.",
     "entities": [], "tags": ["Saffron", "stalled"],
     "state": {"var": "side_project", "value": "paused", "transition": "pause"}},

    {"note_id": "S-008", "timestamp": "2026-01-10T19:35:00", "story_arc_id": "ARC_RELATIONSHIP",
     "summary": "Second date with Lotte - drinks, then walked along the Maas for an hour. Easy to talk to. Didn't expect to be doing this already.",
     "entities": ["Lotte"], "tags": ["Lotte", "dating"],
     "state": {"var": "relationship", "value": "Lotte", "transition": "start"}},

    {"note_id": "S-009", "timestamp": "2026-01-18T11:00:00", "story_arc_id": "ARC_RESIDENCE",
     "summary": "Started seriously looking at places to buy. Booked two viewings for next week. Weird to think about leaving the rental in Rotterdam West after four years.",
     "entities": [], "tags": ["house hunting", "mortgage", "Rotterdam West"],
     "state": {"var": "residence", "value": "rented flat, Rotterdam West", "transition": "search"}},

    {"note_id": "S-010", "timestamp": "2026-01-25T19:05:00", "story_arc_id": "ARC_NOISE",
     "summary": "Made a decent dal. Almost added the recipe to Saffron out of habit, then remembered I'm not doing that right now. Ate on the couch.",
     "entities": [], "tags": ["cooking", "Saffron"], "state": None},

    {"note_id": "S-011", "timestamp": "2026-02-05T16:48:00", "story_arc_id": "ARC_RESIDENCE",
     "summary": "Put an offer on the Capelle house. Over asking. Felt slightly sick clicking send on the bid form.",
     "entities": [], "tags": ["Capelle", "offer", "house"],
     "state": {"var": "residence", "value": "Capelle house", "transition": "bid"}},

    {"note_id": "S-012", "timestamp": "2026-02-10T17:30:00", "story_arc_id": "ARC_EMPLOYMENT",
     "summary": "Cleared my desk at Meridian. HR walked me through the offboarding doc and took the badge back. Severance covers a couple of months. Quiet train home.",
     "entities": ["Meridian Logistics"], "tags": ["Meridian", "layoff", "offboarding"],
     "state": {"var": "employment", "value": "Meridian Logistics", "transition": "job_loss"}},

    {"note_id": "S-013", "timestamp": "2026-02-25T18:15:00", "story_arc_id": "ARC_RESIDENCE",
     "summary": "Lost the Capelle place. Agent said another buyer went in higher with no conditions. Back to the listings.",
     "entities": [], "tags": ["Capelle", "rejected", "house hunting"],
     "state": {"var": "residence", "value": "Capelle house", "transition": "bid_lost"}},

    {"note_id": "S-014", "timestamp": "2026-03-02T10:20:00", "story_arc_id": "ARC_EMPLOYMENT",
     "summary": "Sent out a batch of applications this week. Joost passed my CV to someone he knows at Polder Health. Nice of him.",
     "entities": ["Joost", "Polder Health"], "tags": ["job search", "applications", "Polder", "Joost"],
     "state": {"var": "employment", "value": "(searching)", "transition": "apply"}},

    {"note_id": "S-015", "timestamp": "2026-03-05T22:00:00", "story_arc_id": "ARC_RELATIONSHIP",
     "summary": "Lotte and I called it. No drama, it just quietly ran out of road. Said we'd stay friendly and probably won't.",
     "entities": ["Lotte"], "tags": ["Lotte", "ended"],
     "state": {"var": "relationship", "value": "Lotte", "transition": "end"}},

    {"note_id": "S-016", "timestamp": "2026-03-12T15:40:00", "story_arc_id": "ARC_EMPLOYMENT",
     "summary": "Interview at Kasten Bank. Two rounds back to back. The system-design round was rough - blanked on sharding for a second.",
     "entities": ["Kasten Bank"], "tags": ["interview", "Kasten"],
     "state": {"var": "employment", "value": "Kasten Bank", "transition": "interview"}},

    {"note_id": "S-017", "timestamp": "2026-03-18T13:05:00", "story_arc_id": "ARC_EMPLOYMENT",
     "summary": "Kasten Bank passed. 'Strong candidate, went with someone more senior.' Stings a bit more than I expected.",
     "entities": ["Kasten Bank"], "tags": ["Kasten", "rejection"],
     "state": {"var": "employment", "value": "Kasten Bank", "transition": "rejected"}},

    {"note_id": "S-018", "timestamp": "2026-03-20T12:30:00", "story_arc_id": "ARC_RESIDENCE",
     "summary": "Viewed a flat in Kralingen this morning - light, second floor, small balcony. Put in an offer by the afternoon. Trying not to get attached.",
     "entities": [], "tags": ["Kralingen", "offer", "flat"],
     "state": {"var": "residence", "value": "Kralingen flat", "transition": "bid"}},

    {"note_id": "S-019", "timestamp": "2026-03-22T16:10:00", "story_arc_id": "ARC_PROJECT",
     "summary": "Opened the Saffron repo again for the first time in months. Fixed the broken build, added a grocery-list export. Felt good to type.",
     "entities": [], "tags": ["Saffron", "resumed"],
     "state": {"var": "side_project", "value": "resumed/active", "transition": "resume"}},

    {"note_id": "S-020", "timestamp": "2026-04-02T17:45:00", "story_arc_id": "ARC_RESIDENCE",
     "summary": "They accepted the Kralingen offer. Actually accepted it. Mortgage advisor on Tuesday, keys end of May if the paperwork behaves.",
     "entities": [], "tags": ["Kralingen", "accepted", "mortgage"],
     "state": {"var": "residence", "value": "Kralingen flat", "transition": "bid_accepted"}},

    {"note_id": "S-021", "timestamp": "2026-04-08T14:00:00", "story_arc_id": "ARC_NOISE",
     "summary": "Dentist, then dropped the bike at Rik's for a new chain. Lost half a day to errands. Nothing exciting.",
     "entities": [], "tags": ["errands", "admin"], "state": None},

    {"note_id": "S-022", "timestamp": "2026-04-12T23:20:00", "story_arc_id": "ARC_RELATIONSHIP",
     "summary": "Priya came over. We talked for hours, the real kind. We're going to try again, slowly. Didn't tell anyone yet.",
     "entities": ["Priya"], "tags": ["Priya", "reconciliation"],
     "state": {"var": "relationship", "value": "Priya", "transition": "reconcile"}},

    {"note_id": "S-023", "timestamp": "2026-04-15T15:55:00", "story_arc_id": "ARC_EMPLOYMENT",
     "summary": "Final round at Polder Health. Met the whole backend team, paired on a real bug for an hour. Felt like a place I could actually work.",
     "entities": ["Polder Health"], "tags": ["interview", "Polder"],
     "state": {"var": "employment", "value": "Polder Health", "transition": "interview"}},

    {"note_id": "S-024", "timestamp": "2026-04-20T18:40:00", "story_arc_id": "ARC_EMPLOYMENT",
     "summary": "Bright Harbor sent an offer through. The money's strong. But something about how the team talked over each other in the loop is sitting wrong with me.",
     "entities": ["Bright Harbor"], "tags": ["Bright Harbor", "offer"],
     "state": {"var": "employment", "value": "Bright Harbor", "transition": "offer"}},

    {"note_id": "S-025", "timestamp": "2026-04-28T19:10:00", "story_arc_id": "ARC_EMPLOYMENT",
     "summary": "Told Bright Harbor no. Hanna the recruiter thinks I'm crazy to walk away from that number. Maybe. Slept fine though.",
     "entities": ["Bright Harbor", "Hanna"], "tags": ["Bright Harbor", "declined", "recruiter"],
     "state": {"var": "employment", "value": "Bright Harbor", "transition": "offer_declined"}},

    {"note_id": "S-026", "timestamp": "2026-05-05T17:25:00", "story_arc_id": "ARC_EMPLOYMENT",
     "summary": "Polder Health offer came through. Lower than the other one, but the team's the reason I'd go in on a Monday. Asked for two days to think.",
     "entities": ["Polder Health"], "tags": ["Polder", "offer"],
     "state": {"var": "employment", "value": "Polder Health", "transition": "offer"}},

    {"note_id": "S-027", "timestamp": "2026-05-08T10:05:00", "story_arc_id": "ARC_EMPLOYMENT",
     "summary": "Signed with Polder Health this morning. Start date is the 18th. Backend role, mostly their patient-scheduling service. Relief more than excitement, but I'll take it.",
     "entities": ["Polder Health"], "tags": ["Polder", "signed", "contract"],
     "state": {"var": "employment", "value": "Polder Health", "transition": "accepted"}},

    {"note_id": "S-028", "timestamp": "2026-05-12T20:30:00", "story_arc_id": "ARC_NOISE",
     "summary": "Fenna called, mostly about mum's birthday plans. Told her the short version of the job news. She's relieved for me.",
     "entities": ["Fenna"], "tags": ["family", "Fenna"], "state": None},

    {"note_id": "S-029", "timestamp": "2026-05-18T19:50:00", "story_arc_id": "ARC_EMPLOYMENT",
     "summary": "First day at Polder Health. Laptop setup ate the morning, met my onboarding buddy, drowning in acronyms by 3pm. The scheduling service is older than I hoped.",
     "entities": ["Polder Health"], "tags": ["Polder", "first day", "onboarding"],
     "state": {"var": "employment", "value": "Polder Health", "transition": "start"}},

    {"note_id": "S-030", "timestamp": "2026-05-20T22:15:00", "story_arc_id": "ARC_PROJECT",
     "summary": "Archived the Saffron repo. Set it read-only and wrote a short 'this is done' line in the README. Not going to keep pretending I'll come back to it.",
     "entities": [], "tags": ["Saffron", "archived", "abandoned"],
     "state": {"var": "side_project", "value": "abandoned", "transition": "abandon"}},

    {"note_id": "S-031", "timestamp": "2026-05-24T16:40:00", "story_arc_id": "ARC_RESIDENCE",
     "summary": "Moved into the Kralingen flat. Boxes everywhere, fridge not connected yet. Priya helped carry the heavy stuff and we ate pizza on the floor.",
     "entities": ["Priya"], "tags": ["Kralingen", "moving"],
     "state": {"var": "residence", "value": "Kralingen flat", "transition": "moved_in"}},

    {"note_id": "S-032", "timestamp": "2026-05-26T21:00:00", "story_arc_id": "ARC_RELATIONSHIP",
     "summary": "Unpacked the kitchen with Priya. She found the old ramen receipt from the Markthal place in a box and we both went quiet for a second, the good kind.",
     "entities": ["Priya"], "tags": ["Priya", "home"],
     "state": {"var": "relationship", "value": "Priya", "transition": "present"}},

    {"note_id": "S-033", "timestamp": "2026-05-28T22:05:00", "story_arc_id": "ARC_NOISE",
     "summary": "Climbing with Joost again. Complained about the new commute to Polder - two transfers - but honestly it's fine. He sent me a flat-white meme after.",
     "entities": ["Joost", "Polder Health"], "tags": ["climbing", "Joost", "commute"], "state": None},

    {"note_id": "S-034", "timestamp": "2026-05-30T18:20:00", "story_arc_id": "ARC_EMPLOYMENT",
     "summary": "Two weeks in at Polder. The way they do deploys is the opposite of how we did it at Meridian - everything through one big pipeline nobody fully trusts. Keeping my opinions to myself for now.",
     "entities": ["Polder Health", "Meridian Logistics"], "tags": ["Polder", "Meridian", "work"],
     "state": {"var": "employment", "value": "Polder Health", "transition": "context"}},
]

NOTE_EXPANSION_PROMPT = """You are converting a structured journal event into a realistic personal note in Niels's voice.

Niels is a 32-year-old backend software developer in Rotterdam. He writes notes to himself in a lived-in, imperfect, fragmentary style - like real journal entries, not polished prose. Sometimes incomplete sentences. Sometimes dry or self-deprecating. Never resolved or wrapped up neatly.

Rules:
- Keep it short (50-120 words).
- First-person, in Niels's voice.
- Do NOT add facts that aren't in the event summary.
- Describe ONLY this single moment. Do NOT summarize how things got here or where they are heading.
- NEVER use status labels like "former", "ex", "current", "new job", "now works at", "used to". The reader must infer status from dates and other notes - your note must not give it away.
- Do NOT add psychological interpretation or causal explanation that isn't in the summary.
- It's fine for the note to feel unfinished.
- No headers, no bullet points, no quotes around the text. Just the note text.

Event to expand:
- date/time: {timestamp}
- summary: {summary}
- people mentioned: {entities}

Write ONLY the note text.
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
    if text.startswith(("'", '"', "`")) and text.endswith(("'", '"', "`")):
        text = text[1:-1].strip()
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="regenerate even if notes.json exists")
    parser.add_argument("--raw", action="store_true", help="skip the LLM; use summaries verbatim")
    args = parser.parse_args()

    if NOTES_PATH.exists() and not args.force:
        print(f"{NOTES_PATH.name} already exists; pass --force to regenerate.")
        return 0

    if args.raw:
        model = host = None
        print(f"Building {len(EVENTS)} notes from summaries (--raw, no LLM)")
    else:
        model = get_setting("chat_model")
        host = get_setting("ollama_host")
        print(f"Generating {len(EVENTS)} notes with model={model} host={host}")

    notes = []
    for i, event in enumerate(EVENTS, start=1):
        print(f"  [{i:2d}/{len(EVENTS)}] {event['note_id']} ({event['timestamp']})...", flush=True)
        if args.raw:
            text = event["summary"]
        else:
            try:
                text = expand_event(event, model, host)
            except Exception as exc:
                print(f"    FAILED: {exc}", file=sys.stderr)
                text = event["summary"]
        notes.append({
            "note_id": event["note_id"],
            "timestamp": event["timestamp"],
            "text": text,
            "entities": event["entities"],
            "tags": event["tags"],
            "story_arc_id": event["story_arc_id"],
            "state": event["state"],
        })

    notes.sort(key=lambda n: n["timestamp"])
    NOTES_PATH.write_text(json.dumps(notes, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(notes)} notes to {NOTES_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
