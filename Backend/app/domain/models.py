# app/domain/models.py
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Recording:
    id: str
    path: str
    language: str = "en"
    duration_s: Optional[float] = None

@dataclass
class Transcript:
    recording_id: str
    text: str
    words: Optional[List[dict]] = None

@dataclass
class Segment:
    recording_id: str
    start_s: float
    end_s: float
    label: str
    text: Optional[str] = None

@dataclass
class PiiFinding:
    recording_id: str
    start_char: int
    end_char: int
    label: str
    preview: str
