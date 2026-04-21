from pydantic import BaseModel, field_validator
from typing import List


class TagCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def normalise(cls, v: str) -> str:
        return v.strip().lower()


class TagRead(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class TagSuggestion(BaseModel):
    """A single LLM-suggested tag — not yet persisted."""
    name: str
    reason: str  # short explanation so the user understands why it was suggested


class TagSuggestionsResponse(BaseModel):
    suggestions: List[TagSuggestion]


class BulkTagConfirm(BaseModel):
    """
    The names the user chose to keep after reviewing LLM suggestions.
    Frontend sends whatever subset the user didn't delete/edit.
    """
    names: List[str]

    @field_validator("names")
    @classmethod
    def normalise_all(cls, v: List[str]) -> List[str]:
        return [name.strip().lower() for name in v if name.strip()]
    
class SourceInTagRead(BaseModel):
    id: int
    filename: str | None = None
    file_type: str | None = None
    model_config = {"from_attributes": True}

class TagWithSourcesRead(BaseModel):
    id: int
    name: str
    sources: List[SourceInTagRead] = []
    model_config = {"from_attributes": True}