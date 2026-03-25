from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

from pydantic import BaseModel


class Mode(str, Enum):
    clarifying = "clarifying"
    deep_dive = "deep_dive"


class StepN(int, Enum):
    description = 1
    feelings = 2
    evaluation = 3
    analysis = 4
    conclusion = 5
    action = 6


class TopicSchema(BaseModel):
    name: str
    summary: str
    quotes: list[str]


class GenerateRequest(BaseModel):
    mode: Mode
    step: StepN | None = None
    topic: str | None = None
    topic_summary: str | None = None
    history: list[dict] | None = None


class TopicResponse(BaseModel):
    topics: list[TopicSchema]
    journal_text: str


class SaveAnswerRequest(BaseModel):
    journal_id: int
    question_text: str
    answer_text: str
    topic_id: int | None = None

@dataclass  
class SimpleRecording:
    path: str
    id: str    

@dataclass
class WordToken:
    word: str
    start_s: Optional[float] = None
    end_s: Optional[float] = None
    prob: Optional[float] = None

@dataclass
class Sentence:
    id: int
    text: str
    start_s: Optional[float] = None
    end_s: Optional[float] = None
    meta: dict = field(default_factory=dict)

@dataclass
class Transcript:
    recording_id: str
    text: str
    words: list[WordToken] = field(default_factory=list)
    sentences: list[Sentence] = field(default_factory=list)
    source: str = "whisperx"

class QuerySource(BaseModel):
    journal_id: str | None = None
    chunk_id: str | None = None
    score: float | None = None
    node_id: str | None = None
    text: str

class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: list[QuerySource]