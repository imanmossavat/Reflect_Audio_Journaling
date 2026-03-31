from datetime import datetime
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


# ─── Many to Many table ───────────────────────────────────────────────────────────

class JournalTag(SQLModel, table=True):
    __tablename__ = "journal_tag"

    journal_id: int = Field(foreign_key="journal.id", primary_key=True)
    tag_id: int = Field(foreign_key="tag.id", primary_key=True)


class QuestionTag(SQLModel, table=True):
    __tablename__ = "question_tag"

    question_id: int = Field(foreign_key="question.id", primary_key=True)
    tag_id: int = Field(foreign_key="tag.id", primary_key=True)


# ─── Tables ──────────────────────────────────────────────────────────────

class TagCluster(SQLModel, table=True):
    __tablename__ = "tag_cluster"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255, unique=True)
    description: Optional[str] = Field(default=None)

    # Relationships
    tags: List["Tag"] = Relationship(back_populates="tag_cluster")
    scale_questions: List["ScaleQuestion"] = Relationship(back_populates="tag_cluster")


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
    questions: List["Question"] = Relationship(back_populates="journal")
    tags: List["Tag"] = Relationship(back_populates="journals", link_model=JournalTag)


class Chunk(SQLModel, table=True):
    __tablename__ = "chunk"

    id: Optional[int] = Field(default=None, primary_key=True)
    journal_id: int = Field(foreign_key="journal.id")
    chunk_text: str
    chunk_index: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    journal: Optional[Journal] = Relationship(back_populates="chunks")


class Tag(SQLModel, table=True):
    __tablename__ = "tag"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255)
    tag_cluster_id: int = Field(foreign_key="tag_cluster.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    journals: List[Journal] = Relationship(back_populates="tags", link_model=JournalTag)
    questions: List["Question"] = Relationship(back_populates="tags", link_model=QuestionTag)
    tag_cluster: Optional[TagCluster] = Relationship(back_populates="tags")


class Question(SQLModel, table=True):
    __tablename__ = "question"

    id: Optional[int] = Field(default=None, primary_key=True)
    journal_id: int = Field(foreign_key="journal.id")
    question_text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    journal: Optional[Journal] = Relationship(back_populates="questions")
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
    question_text: str
    scale_max: int
    tag_cluster_id: int = Field(foreign_key="tag_cluster.id")
    is_active: bool = Field(default=True)

    # Relationships
    tag_cluster: Optional[TagCluster] = Relationship(back_populates="scale_questions")
    responses: List["ScaleResponse"] = Relationship(back_populates="scale_question")


class ScaleResponse(SQLModel, table=True):
    __tablename__ = "scale_response"

    id: Optional[int] = Field(default=None, primary_key=True)
    scale_question_id: int = Field(foreign_key="scale_question.id")
    answer: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    scale_question: Optional[ScaleQuestion] = Relationship(back_populates="responses")