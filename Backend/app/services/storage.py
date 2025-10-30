import os
import uuid
import datetime
import json

from typing import Any, Dict, Tuple
from app.core.config import settings

class StorageManager:
    """
    Handles file storage and metadata linking for recordings, transcripts, and related data.
    """

    def __init__(self):
        self.base = settings.DATA_DIR
        os.makedirs(self.base, exist_ok=True)

    # ---------------- PUBLIC METHODS ---------------- #

    def save_upload(self, filename: str, file_bytes: bytes) -> Tuple[str, str]:
        """
        Saves an uploaded audio file to the data directory.
        Returns (recording_id, full_file_path)
        """
        now = datetime.datetime.utcnow()
        recording_id = uuid.uuid4().hex[:12]

        rel_dir = f"audio/{now:%Y/%m/%d}"
        abs_dir = os.path.join(self.base, rel_dir)
        os.makedirs(abs_dir, exist_ok=True)

        # ensure consistent file naming
        safe_name = os.path.basename(filename).replace(" ", "_")
        final_name = f"{now:%Y%m%d_%H%M%S}_{recording_id}_{safe_name}"
        path = os.path.join(abs_dir, final_name)

        with open(path, "wb") as f:
            f.write(file_bytes)

        print(f"[StorageManager] Saved upload: {path}")
        return recording_id, path

    def save_json(self, rel_path: str, data: Dict[str, Any]) -> str:
        """
        Saves structured data (e.g., transcripts, summaries) as JSON.
        Returns the full path to the saved file.
        """
        abs_path = os.path.join(self.base, rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[StorageManager] Saved JSON: {abs_path}")
        return abs_path

    def link_objects(self, audio_path: str, transcript_path: str = None, summary_path: str = None) -> str:
        """
        Creates or updates a metadata JSON linking related files.
        Returns path to metadata file.
        """
        metadata = {
            "audio": audio_path,
            "transcript": transcript_path,
            "summary": summary_path,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }

        meta_dir = os.path.join(self.base, "metadata")
        os.makedirs(meta_dir, exist_ok=True)
        meta_path = os.path.join(meta_dir, f"{uuid.uuid4().hex[:12]}_meta.json")

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        print(f"[StorageManager] Linked metadata: {meta_path}")
        return meta_path

    def load_json(self, rel_path: str) -> Dict[str, Any]:
        """
        Loads JSON data from disk.
        """
        abs_path = os.path.join(self.base, rel_path)
        with open(abs_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_recordings(self) -> list:
        """
        Returns all stored recordings (basic scan, no DB).
        """
        audio_dir = os.path.join(self.base, "audio")
        recordings = []
        for root, _, files in os.walk(audio_dir):
            for f in files:
                if f.lower().endswith((".wav", ".mp3", ".m4a", ".webm")):
                    recordings.append(os.path.join(root, f))
        return recordings

    # ---------------- PRIVATE HELPERS ---------------- #

    def _make_path(self, category: str, extension: str) -> str:
        """
        Generates a consistent path for a given data type (audio, transcript, summary, etc.)
        """
        now = datetime.datetime.utcnow()
        uid = uuid.uuid4().hex[:12]
        rel_dir = f"{category}/{now:%Y/%m/%d}"
        os.makedirs(os.path.join(self.base, rel_dir), exist_ok=True)
        return os.path.join(rel_dir, f"{now:%Y%m%d_%H%M%S}_{uid}.{extension}")
