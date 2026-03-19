# app/domain/models.py
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

@dataclass
class Recording:
    id: str
    path: str
    language: str = "en"
    duration_s: Optional[float] = None

@dataclass
class WordToken:
    word: str
    start_s: float
    end_s: float
    prob: Optional[float] = None

@dataclass
class Sentence:
    id: int
    start_s: float
    end_s: float
    text: str
    # keep flexible for speaker tags, etc.
    meta: Optional[Dict[str, Any]] = None

@dataclass
class Transcript:
    recording_id: str
    text: str
    words: Optional[List[WordToken]] = None
    sentences: Optional[List[Sentence]] = None
    source: str = "whisperx"

@dataclass
class Segment:
    recording_id: str
    id: int
    start_s: float
    end_s: float
    label: str
    sentence_ids: Optional[List[int]] = None
    text: Optional[str] = None

@dataclass
class ProsodyFeatures:
    recording_id: str
    sentence_id: Optional[int] = None
    segment_id: Optional[int] = None

    rms_mean: Optional[float] = None
    rms_var: Optional[float] = None

    speaking_rate_wpm: Optional[float] = None
    pause_ratio: Optional[float] = None

@dataclass
class PiiFinding:
    recording_id: str
    start_char: int
    end_char: int
    label: str
    preview: str
