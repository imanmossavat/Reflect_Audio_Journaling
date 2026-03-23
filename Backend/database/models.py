from datetime import datetime
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


# ─── Many to Many table ───────────────────────────────────────────────────────────

class JournalTag(SQLModel, table=True):
    __tablename__ = "journaltag"

    journal_id: int = Field(foreign_key="journal.id", primary_key=True)
    tag_id: int = Field(foreign_key="tag.id", primary_key=True)


# ─── Tables ──────────────────────────────────────────────────────────────

class Journal(SQLModel, table=True):
    __tablename__ = "journal"

    id: Optional[int] = Field(default=None, primary_key=True)
    filename: Optional[str] = Field(default=None, max_length=255)
    file_type: Optional[str] = Field(default=None, max_length=255)
    file_path: Optional[str] = Field(default=None)
    text: Optional[str] = Field(default=None) 
    status: str = Field(max_length=255, default="not processed")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    edited_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    chunks: List["Chunk"] = Relationship(back_populates="journal")
    topics: List["Topic"] = Relationship(back_populates="journal")
    questions: List["Question"] = Relationship(back_populates="journal")
    tags: List["Tag"] = Relationship(back_populates="journals", link_model=JournalTag)


class Chunk(SQLModel, table=True):
    __tablename__ = "chunk"

    id: Optional[int] = Field(default=None, primary_key=True)
    journal_id: int = Field(foreign_key="journal.id")
    chunk_text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    journal: Optional[Journal] = Relationship(back_populates="chunks")


class Tag(SQLModel, table=True):
    __tablename__ = "tag"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255)

    # Relationships
    journals: List[Journal] = Relationship(back_populates="tags", link_model=JournalTag)


class Topic(SQLModel, table=True):
    __tablename__ = "topics"

    id: Optional[int] = Field(default=None, primary_key=True)
    journal_id: int = Field(foreign_key="journal.id")
    name: str = Field(max_length=255)
    summary: str = Field(max_length=255)

    # Relationships
    journal: Optional[Journal] = Relationship(back_populates="topics")
    questions: List["Question"] = Relationship(back_populates="topic")
    quotes: List["TopicQuote"] = Relationship(back_populates="topic")


class Question(SQLModel, table=True):
    __tablename__ = "question"

    id: Optional[int] = Field(default=None, primary_key=True)
    journal_id: int = Field(foreign_key="journal.id")
    topic_id: Optional[int] = Field(default=None, foreign_key="topics.id")
    question_text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    journal: Optional[Journal] = Relationship(back_populates="questions")
    topic: Optional[Topic] = Relationship(back_populates="questions")
    answers: List["Answer"] = Relationship(back_populates="question")


class Answer(SQLModel, table=True):
    __tablename__ = "answer"

    id: Optional[int] = Field(default=None, primary_key=True)
    question_id: int = Field(foreign_key="question.id")
    answer_text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    question: Optional[Question] = Relationship(back_populates="answers")


class TopicQuote(SQLModel, table=True):
    __tablename__ = "topicquotes"

    id: Optional[int] = Field(default=None, primary_key=True)
    topic_id: int = Field(foreign_key="topics.id")
    quote: str

    # Relationships
    topic: Optional[Topic] = Relationship(back_populates="quotes")