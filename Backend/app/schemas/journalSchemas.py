from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

from pydantic import BaseModel


class Mode(str, Enum):
    clarifying = "clarifying"
    deep_dive = "deep_dive"
    # Conversational facilitator responding to a user's typed answer within a stage.
    reply = "reply"
    # "Answer" lever: record the message and update Gist/Open Thread, no facilitator
    # reply generated. See Backend/app/services/reflectionLoop.run_reflect_only.
    reflect = "reflect"


class StepN(int, Enum):
    description = 1
    feelings = 2
    evaluation = 3
    analysis = 4
    conclusion = 5
    action = 6


class ExtractedTagSchema(BaseModel):
    name: str
    summary: str
    quotes: list[str]


class GenerateRequest(BaseModel):
    mode: Mode
    # chat_id identifies the reflection_state row (Document B §2) this turn reads/writes.
    # Required — every structured-reflection turn belongs to exactly one chat.
    chat_id: int
    # `step` is accepted for backward compatibility with the existing frontend payload
    # but is no longer used as a gating mechanism (Document B §9) — Focus/Gist/Open
    # Thread, not a stage counter, drive the turn now.
    step: StepN | None = None
    focus_tag: str | None = None
    focus_tag_summary: str | None = None
    history: list[dict] | None = None
    journal_text: str | None = None
    # Accepted for backward compatibility; unused — Focus now comes from the chat's
    # already-persisted reflection_goal (see reflectionStateService.ensure_state).
    goal: str | None = None
    scope_items: list[str] | None = None


class ExtractedTagsResponse(BaseModel):
    tags: list[ExtractedTagSchema]
    source_text: str


class SaveAnswerRequest(BaseModel):
    source_id: int
    question_text: str
    answer_text: str


class SourcePatchRequest(BaseModel):
    text: str | None = None
    text_html: str | None = None  # rich HTML for display; plain text is derived from it
    summary: str | None = None  # user-edited summary; does not trigger reprocessing
    summary_html: str | None = None  # rich HTML for the summary; plain summary derived from it
    filename: str | None = None
    created_at: str | None = None  # ISO 8601 datetime string

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
    # Provenance: model/device/OS/timing for this transcription run, e.g.
    # {"model": "medium", "device": "cuda", "os": ..., "duration_s": ..., "finished_at": ...}.
    meta: dict = field(default_factory=dict)

class QuerySource(BaseModel):
    source_id: str | None = None
    chunk_id: str | None = None
    score: float | None = None
    node_id: str | None = None
    text: str

class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: list[QuerySource]
    model_used: str | None = None