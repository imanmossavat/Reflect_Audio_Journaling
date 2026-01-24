from pathlib import Path
from typing import List, Any
from .base import FileEngine
from .metadata import MetadataService

class TranscriptService:
    """
    Manages transcript text files and alignments.
    """

    def __init__(self, engine: FileEngine, metadata: MetadataService):
        self.engine = engine
        self.metadata = metadata

    def save_transcript(self, recording_id: str, text: str, version: str = "original") -> str:
        rel_path = f"transcripts/{recording_id}/{version}.txt"
        self.engine.write_text(rel_path, text)
        return rel_path

    def save_words(self, recording_id: str, words: List[Any], version: str = "original") -> str:
        rel_path = f"transcripts/{recording_id}/aligned_words.json"
        
        payload = []
        for w in (words or []):
            if isinstance(w, dict):
                payload.append(w)
            else:
                payload.append(getattr(w, "__dict__", {"value": str(w)}))

        self.engine.write_json(rel_path, payload)
        return rel_path

    def save_segments(self, recording_id: str, segments: List[Any]) -> str:
        rel_path = f"segments/{recording_id}/{recording_id}.json"
        data = {"segments": [s.__dict__ for s in segments]}
        self.engine.write_json(rel_path, data)
        return rel_path

    def delete_transcript(self, recording_id: str, version: str) -> bool:
        try:
            meta = self.metadata.load_metadata(recording_id)
        except FileNotFoundError:
            return False
            
        rel = (meta.get("transcripts") or {}).get(version)
        if not rel:
            return False
            
        self.engine.delete_file(rel)
        meta.setdefault("transcripts", {})
        meta["transcripts"][version] = None
        self.metadata.save_metadata(recording_id, meta)
        return True
