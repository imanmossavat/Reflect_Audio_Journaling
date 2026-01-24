"""
Storage Service Package

This provides a unified place (StorageManager) for the application while delegating 
concerns to other services:
- FileEngine: Low-level filesystem operations and path resolution.
- MetadataService: Recording metadata lifecycle management.
- AudioStorageService: Persistence and management of audio source files.
- TranscriptService: Versioned transcript storage and alignment data.
"""

import os
import shutil
from typing import Any, Dict, Optional, Tuple

from .base import FileEngine
from .metadata import MetadataService
from .audio import AudioStorageService
from .transcripts import TranscriptService

class StorageManager:
    """
    Facade for granular storage services.
    Provides an interface for the domain layer while maintaining 
    backward compatibility.
    """

    def __init__(self, 
                 engine: Optional[FileEngine] = None, 
                 metadata: Optional[MetadataService] = None,
                 audio: Optional[AudioStorageService] = None,
                 transcripts: Optional[TranscriptService] = None):
        
        self.engine = engine or FileEngine()
        self.metadata_svc = metadata or MetadataService(self.engine)
        self.audio_svc = audio or AudioStorageService(self.engine, self.metadata_svc)
        self.transcript_svc = transcripts or TranscriptService(self.engine, self.metadata_svc)
        
        self.base = self.engine.base

    # ---------------- PATH HELPERS ---------------- #

    def abs_path(self, rel_path: str) -> str:
        return self.engine.abs_path(rel_path)

    def exists_rel(self, rel_path: str) -> bool:
        return self.engine.exists(rel_path)

    # ---------------- READ / WRITE ---------------- #

    def save_upload(self, filename: str, file_bytes: bytes) -> Tuple[str, str]:
        return self.audio_svc.save_upload(filename, file_bytes)

    def save_transcript(self, recording_id: str, text: str, version: str = "original") -> str:
        return self.transcript_svc.save_transcript(recording_id, text, version)

    def save_words(self, recording_id: str, words: list, version: str = "original") -> str:
        return self.transcript_svc.save_words(recording_id, words, version)

    def load_text(self, rel_path: str) -> str:
        return self.engine.read_text(rel_path)

    def save_json(self, rel_path: str, data: Dict[str, Any]) -> str:
        self.engine.write_json(rel_path, data)
        return rel_path

    def load_json(self, rel_path: str) -> Dict[str, Any]:
        return self.engine.read_json(rel_path)

    def save_segments(self, recording_id: str, segments: list) -> str:
        return self.transcript_svc.save_segments(recording_id, segments)

    # ---------------- METADATA ---------------- #

    def load_metadata(self, recording_id: str) -> Dict[str, Any]:
        return self.metadata_svc.load_metadata(recording_id)

    def save_metadata(self, recording_id: str, metadata: Dict[str, Any]) -> str:
        return self.metadata_svc.save_metadata(recording_id, metadata)

    # ---------------- DELETION ---------------- #

    def delete_transcript(self, recording_id: str, version: str) -> bool:
        return self.transcript_svc.delete_transcript(recording_id, version)

    def delete_audio(self, recording_id: str) -> bool:
        return self.audio_svc.delete_audio(recording_id)

    def delete_recording(self, recording_id: str) -> bool:
        """
        Deletes all files associated with a recording.
        """
        for rel_dir in [
            f"audio/{recording_id}",
            f"transcripts/{recording_id}",
            f"segments/{recording_id}",
        ]:
            abs_dir = self.engine.abs_path(rel_dir)
            if os.path.isdir(abs_dir):
                shutil.rmtree(abs_dir, ignore_errors=True)
    
        self.metadata_svc.delete_metadata(recording_id)
    
        # Cleanup parent dirs
        self.engine.prune_empty_dirs(self.engine.abs_path("audio"))
        self.engine.prune_empty_dirs(self.engine.abs_path("transcripts"))
        self.engine.prune_empty_dirs(self.engine.abs_path("segments"))
        self.engine.prune_empty_dirs(self.engine.abs_path("metadata"))
    
        return True
