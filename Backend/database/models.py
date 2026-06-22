from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, SQLModel


#Many-to-many tables

class SourceTag(SQLModel, table=True):
    __tablename__ = "source_tag"

    source_id: int = Field(foreign_key="source.id", primary_key=True)
    tag_id: int = Field(foreign_key="tag.id", primary_key=True)
    # Provenance: "llm" for auto-extracted on ingest, "user" for hand-added. Lets a
    # recompute refresh only LLM tags while preserving the user's manual edits.
    origin: str = Field(max_length=20, default="user")


class QuestionTag(SQLModel, table=True):
    __tablename__ = "question_tag"

    question_id: int = Field(foreign_key="question.id", primary_key=True)
    tag_id: int = Field(foreign_key="tag.id", primary_key=True)


#Tables

class Source(SQLModel, table=True):
    __tablename__ = "source"

    id: Optional[int] = Field(default=None, primary_key=True)
    filename: Optional[str] = Field(default=None, max_length=255)
    file_type: Optional[str] = Field(default=None, max_length=255)
    file_path: Optional[str] = Field(default=None)
    text: Optional[str] = Field(default=None)
    # Rich HTML for display only. The plain-text `text` above stays the value used for chunking, embeddings, tags and chat context.
    text_html: Optional[str] = Field(default=None)
    transcript_segments: Optional[list] = Field(default=None, sa_column=Column(JSON))
    # LLM-generated one-paragraph summary produced during ingest enrichment.
    summary: Optional[str] = Field(default=None)
    # Rich HTML for the summary editor. Plain-text `summary` above is derived from it
    # and stays the value used elsewhere (lists, RAG context).
    summary_html: Optional[str] = Field(default=None)
    # Provenance/versioning for recomputable derived artifacts, e.g.
    # {"summary": {"model": ..., "prompt_version": ..., "generated_at": ...}, "tags": {...}}.
    # Kept as JSON so new artifacts (entities, etc.) can be added without a migration.
    derived_meta: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    status: str = Field(max_length=255, default="not processed")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    edited_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    chunks: List["Chunk"] = Relationship(back_populates="source")
    questions: List["Question"] = Relationship(back_populates="source")
    scale_questions: List["ScaleQuestion"] = Relationship(back_populates="source")
    tags: List["Tag"] = Relationship(back_populates="sources", link_model=SourceTag)


class Chunk(SQLModel, table=True):
    __tablename__ = "chunk"

    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: int = Field(foreign_key="source.id")
    chunk_text: str
    chunk_index: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    source: Optional[Source] = Relationship(back_populates="chunks")


class Tag(SQLModel, table=True):
    __tablename__ = "tag"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    sources: List[Source] = Relationship(back_populates="tags", link_model=SourceTag)
    questions: List["Question"] = Relationship(back_populates="tags", link_model=QuestionTag)


class Question(SQLModel, table=True):
    __tablename__ = "question"

    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: int = Field(foreign_key="source.id")
    question_text: str
    trigger_type: Optional[str] = Field(default=None, max_length=100)
    trigger_context: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    source: Optional[Source] = Relationship(back_populates="questions")
    answers: List["Answer"] = Relationship(back_populates="question")
    tags: List[Tag] = Relationship(back_populates="questions", link_model=QuestionTag)


class Answer(SQLModel, table=True):
    __tablename__ = "answer"

    id: Optional[int] = Field(default=None, primary_key=True)
    question_id: int = Field(foreign_key="question.id")
    answer_text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    question: Optional[Question] = Relationship(back_populates="answers")


class ScaleQuestion(SQLModel, table=True):
    __tablename__ = "scale_question"

    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: int = Field(foreign_key="source.id")
    question_text: str
    scale_max: int
    trigger_type: str = Field(max_length=100)
    trigger_context: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    # Relationships
    source: Optional[Source] = Relationship(back_populates="scale_questions")
    responses: List["ScaleResponse"] = Relationship(back_populates="scale_question")


class ScaleResponse(SQLModel, table=True):
    __tablename__ = "scale_response"

    id: Optional[int] = Field(default=None, primary_key=True)
    scale_question_id: int = Field(foreign_key="scale_question.id")
    answer: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    scale_question: Optional[ScaleQuestion] = Relationship(back_populates="responses")


class Chat(SQLModel, table=True):
    __tablename__ = "chat"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=255, default="Untitled")
    source_id: Optional[int] = Field(default=None, foreign_key="source.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    edited_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    messages: List["ChatMessage"] = Relationship(back_populates="chat")


class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_message"

    id: Optional[int] = Field(default=None, primary_key=True)
    chat_id: int = Field(foreign_key="chat.id")
    role: str = Field(max_length=20)
    text: str
    scale_value: Optional[int] = Field(default=None)
    scale_max: Optional[int] = Field(default=None)
    scale_low_label: Optional[str] = Field(default=None, max_length=100)
    scale_high_label: Optional[str] = Field(default=None, max_length=100)
    model: Optional[str] = Field(default=None, max_length=255)
    thinking: Optional[str] = Field(default=None)
    # Gibbs stage (1-6) this message belongs to during a guided reflection; None for
    # ordinary chat messages. Lets the UI group questions/answers by reflection step.
    gibbs_step: Optional[int] = Field(default=None)
    # Retrieved source chunks backing a RAG ("context question") answer; None otherwise.
    # Lets the UI show source chips under the answer, persisted across reloads.
    sources: Optional[list] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    chat: Optional[Chat] = Relationship(back_populates="messages")