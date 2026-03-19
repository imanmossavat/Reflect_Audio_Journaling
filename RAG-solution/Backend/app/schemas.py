from enum import Enum

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
