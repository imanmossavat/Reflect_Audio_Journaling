from typing import Any, Dict, Optional
from .base import FileEngine

class MetadataService:
    """
    Handles high-level recording metadata lifecycle.
    """

    def __init__(self, engine: FileEngine):
        self.engine = engine

    def load_metadata(self, recording_id: str) -> Dict[str, Any]:
        rel_path = f"metadata/{recording_id}.json"
        if not self.engine.exists(rel_path):
            raise FileNotFoundError(f"No metadata for recording {recording_id}")
        return self.engine.read_json(rel_path)

    def save_metadata(self, recording_id: str, metadata: Dict[str, Any]) -> str:
        rel_path = f"metadata/{recording_id}.json"
        self.engine.write_json(rel_path, metadata)
        return rel_path

    def delete_metadata(self, recording_id: str):
        rel_path = f"metadata/{recording_id}.json"
        self.engine.delete_file(rel_path)
