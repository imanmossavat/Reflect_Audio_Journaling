import sys
import os
import random
import uuid
import json
import wave
import struct
from datetime import datetime, timedelta, timezone

# Add parent dir to path to allow importing app modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from app.core.config import settings
from app.services.storage import StorageManager

# Lists for generating data
EMOTIONS = ["anxious", "happy", "calm", "frustrated", "hopeful", "tired", "excited", "melancholic", "grateful", "overwhelmed"]
TOPICS = ["School", "Work", "Relationships", "Family", "Health", "Future", "Reflect Project", "Internship", "Hobby"]
SENTENCE_TEMPLATES = [
    "Today was a {adj} day.",
    "I've been thinking a lot about {topic} lately.",
    "It feels like {topic} is taking up all my energy.",
    "I managed to make some progress on {topic} which felt good.",
    "Why do I always feel so {adj} when dealing with {topic}?",
    "I need to focus more on my wellbeing.",
    "The situation with {topic} is getting better.",
    "I am {adj} about what comes next.",
    "Reflecting on today, I realize I was too {adj}.",
    "I want to change how I approach {topic}."
]

def create_silent_wav(path, duration_sec=1):
    """Creates a small silent WAV file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        n_frames = 16000 * duration_sec
        data = struct.pack('<h', 0) * n_frames
        f.writeframes(data)

def generate_entry(store: StorageManager, date_offset: int):
    # 1. Basic Metadata
    recording_id = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc) - timedelta(days=date_offset, hours=random.randint(0, 12), minutes=random.randint(0, 59))
    created_at = now.isoformat()
    
    # 2. Generate Content
    num_sentences = random.randint(5, 15)
    sentences = []
    text_parts = []
    
    current_time_s = 0.0
    
    for _ in range(num_sentences):
        tmpl = random.choice(SENTENCE_TEMPLATES)
        topic = random.choice(TOPICS)
        adj = random.choice(EMOTIONS)
        sent_text = tmpl.format(topic=topic, adj=adj)
        
        duration = len(sent_text.split()) * 0.4 + random.uniform(0.2, 1.0) # Rough estimate
        
        sentences.append({
            "id": len(sentences),
            "start_s": round(current_time_s, 2),
            "end_s": round(current_time_s + duration, 2),
            "text": sent_text
        })
        text_parts.append(sent_text)
        current_time_s += duration

    full_text = " ".join(text_parts)
    duration_total = current_time_s
    
    # 3. Create Audio File
    date_str = now.strftime("%Y%m%d_%H%M%S")
    filename = f"{date_str}_{recording_id}_fake_audio.wav"
    audio_rel = f"audio/{recording_id}/{filename}"
    audio_abs = store.abs_path(audio_rel)
    create_silent_wav(audio_abs, duration_sec=int(duration_total) + 1)
    
    # 4. Save Transcripts
    original_path = store.save_transcript(recording_id, full_text, "original")
    
    # 5. Generate Segments (Fake Topic Segmentation)
    segments = []
    if num_sentences > 3:
        # Split into 1-3 segments
        num_segs = random.randint(1, 3)
        chunk_size = len(sentences) // num_segs
        
        for i in range(num_segs):
            start_idx = i * chunk_size
            end_idx = start_idx + chunk_size if i < num_segs - 1 else len(sentences)
            
            seg_sentences = sentences[start_idx:end_idx]
            if not seg_sentences: continue

            seg_text = " ".join(s["text"] for s in seg_sentences)
            # Pick a main topic for label
            seg_label = random.choice(TOPICS)
            
            segments.append({
                "id": i,
                "start_s": seg_sentences[0]["start_s"],
                "end_s": seg_sentences[-1]["end_s"],
                "text": seg_text,
                "label": seg_label,
                "sentence_ids": [s["id"] for s in seg_sentences]
            })
            
    # Manually save segments to avoid needing Segment objects
    segments_path = f"segments/{recording_id}.json"
    store.save_json(segments_path, {"segments": segments})
    
    # 6. Metadata
    tags = list(set([random.choice(TOPICS) for _ in range(random.randint(1, 4))]))
    tags.append("synthetic")
    
    title = f"Journal: {random.choice(EMOTIONS).capitalize()} about {tags[0]}"
    
    metadata = {
        "recording_id": recording_id,
        "audio": audio_rel, # Relative path expected by frontend
        "language": "en",
        "source": "audio",
        "created_at": created_at,
        "duration": duration_total,
        "aligned_words": None, # Skip complex word alignment for fake data
        "speech": {},
        "title": title,
        "tags": tags,
        
        "transcripts": {
            "original": original_path,
            "edited": None,
            "redacted": None,
        },
        
        "segments": [segments_path],
        "prosody": [], # Skip prosody features
        
        "sentences": sentences,
        "pii": [],
        "pii_original": [],
        "pii_edited": [],
    }
    
    store.save_metadata(recording_id, metadata)
    print(f"Generated: {title} ({recording_id})")

def main():
    print("Initializing StorageManager...")
    store = StorageManager()
    print(f"Data Directory: {store.base}")
    
    count = 50
    print(f"Generating {count} fake entries...")
    
    for i in range(count):
        # Generate with some time spread
        generate_entry(store, date_offset=random.randint(0, 60))
        
    print("Done! Refresh your frontend.")

if __name__ == "__main__":
    main()
