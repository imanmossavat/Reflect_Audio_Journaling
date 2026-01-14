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

    def save_transcript(self, recording_id: str, text: str, version: str = "original") -> str:
        rel_path = f"transcripts/{recording_id}/{version}.txt"
        abs_path = os.path.join(self.base, rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(text)
    
        print(f"[StorageManager] Saved transcript ({version}): {abs_path}")
        return rel_path

    def load_metadata(self, recording_id: str) -> Dict[str, Any]:
        rel_path = f"metadata/{recording_id}.json"
        abs_path = os.path.join(self.base, rel_path)

        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"No metadata for recording {recording_id}")

        with open(abs_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_segments(self, recording_id: str, segments: list) -> str:
        rel_path = self._make_path(f"segments/{recording_id}", "json", recording_id)
        data = {"segments": [s.__dict__ for s in segments]}
        self.save_json(rel_path, data)
        return rel_path

    def load_text(self, rel_path: str) -> str:
        abs_path = os.path.join(self.base, rel_path)
        with open(abs_path, "r", encoding="utf-8") as f:
            return f.read()

    def save_metadata(self, recording_id: str, metadata: Dict[str, Any]) -> str:
        rel_path = f"metadata/{recording_id}.json"
        abs_path = os.path.join(self.base, rel_path)

        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        with open(abs_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        print(f"[StorageManager] Saved metadata: {abs_path}")
        return rel_path

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

    def delete_transcript(self, recording_id: str, version: str) -> bool:
        meta = self.load_metadata(recording_id)
        rel = meta.get("transcripts", {}).get(version)
        if not rel:
            return False
        abs_path = os.path.join(self.base, rel)
        if os.path.exists(abs_path):
            os.remove(abs_path)
        meta["transcripts"][version] = None
        self.save_metadata(recording_id, meta)
        return True

    def delete_audio(self, recording_id: str) -> bool:
        meta = self.load_metadata(recording_id)
        audio_path = meta.get("audio")
        if not audio_path:
            return False
        if os.path.exists(audio_path):
            os.remove(audio_path)
        meta["audio"] = None
        self.save_metadata(recording_id, meta)
        return True

    def delete_recording(self, recording_id: str) -> bool:
        # delete known files from metadata
        meta = self.load_metadata(recording_id)
    
        # audio
        ap = meta.get("audio")
        if ap and os.path.exists(ap):
            os.remove(ap)
    
        # transcripts
        for rel in (meta.get("transcripts") or {}).values():
            if rel:
                abs_path = os.path.join(self.base, rel)
                if os.path.exists(abs_path):
                    os.remove(abs_path)
    
        # segments
        for rel in meta.get("segments", []):
            abs_path = os.path.join(self.base, rel)
            if os.path.exists(abs_path):
                os.remove(abs_path)
    
        # metadata
        meta_path = os.path.join(self.base, f"metadata/{recording_id}.json")
        if os.path.exists(meta_path):
            os.remove(meta_path)
    
        return True

    # ---------------- PRIVATE HELPERS ---------------- #

    def _make_path(self, category: str, extension: str, recording_id: str = None) -> str:
        now = datetime.datetime.utcnow()

        if recording_id is None:
            recording_id = uuid.uuid4().hex[:12]

        rel_dir = f"{category}/{now:%Y/%m/%d}"
        os.makedirs(os.path.join(self.base, rel_dir), exist_ok=True)

        filename = f"{now:%Y%m%d_%H%M%S}_{recording_id}.{extension}"
        return os.path.join(rel_dir, filename)

