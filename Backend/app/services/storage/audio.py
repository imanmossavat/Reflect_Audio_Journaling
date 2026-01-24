import os
import uuid
import datetime
from pathlib import Path
from typing import Tuple
from .base import FileEngine
from .metadata import MetadataService

class AudioStorageService:
    """
    Manages audio file persistence.
    """

    def __init__(self, engine: FileEngine, metadata: MetadataService):
        self.engine = engine
        self.metadata = metadata

    def save_upload(self, filename: str, file_bytes: bytes) -> Tuple[str, str]:
        """
        Saves an uploaded file and returns (recording_id, relative_path).
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        recording_id = uuid.uuid4().hex[:12]
    
        rel_dir = f"audio/{recording_id}"
        safe_name = os.path.basename(filename).replace(" ", "_")
        final_name = f"{now:%Y%m%d_%H%M%S}_{recording_id}_{safe_name}"
    
        rel_path = Path(rel_dir, final_name).as_posix()
        self.engine.write_bytes(rel_path, file_bytes)
    
        return recording_id, rel_path

    def delete_audio(self, recording_id: str) -> bool:
        try:
            meta = self.metadata.load_metadata(recording_id)
        except FileNotFoundError:
            return False
            
        audio_rel = meta.get("audio")
        if not audio_rel:
            return False
            
        self.engine.delete_file(audio_rel)
        meta["audio"] = None
        self.metadata.save_metadata(recording_id, meta)
        return True
