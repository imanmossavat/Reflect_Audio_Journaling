from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.domain.models import PiiFinding
from app.core.config import settings

class SettingsUpdatePayload(BaseModel):
    settings: dict = Field(default_factory=dict)

class UpdateMetaPayload(BaseModel):
    title: Optional[str] = None
    tags: Optional[List[str]] = None

class SaveTranscriptPayload(BaseModel):
    text: str = Field(min_length=1)

class CreateTextRecordingPayload(BaseModel):
    text: str = Field(min_length=1)
    title: Optional[str] = None
    tags: Optional[List[str]] = None
    language: str = settings.LANGUAGE
    run_segmentation: bool = True
    run_pii: bool = True

class SemanticSearchPayload(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = 8
    min_score: float = 0.25
    per_recording_cap: int = 2

class UpdatePIIPayload(BaseModel):
    findings: List[PiiFinding]

class OpenFolderPayload(BaseModel):
    path: str
