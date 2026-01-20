import os
import shutil
import uuid
import datetime
import json
from pathlib import Path
from typing import Any, Dict

from app.core.config import settings


class StorageManager:
    """
    Handles file storage and metadata linking for recordings, transcripts, and related data.

    Path rules (important, because humans love breaking things):
    - Metadata stores ONLY relative paths (posix style with forward slashes).
    - Disk access ALWAYS uses abs_path(rel_path).
    """

    def __init__(self):
        self.base = settings.DATA_DIR
        os.makedirs(self.base, exist_ok=True)

    # ---------------- PATH HELPERS ---------------- #

    def abs_path(self, rel_path: str) -> str:
        return os.path.join(self.base, rel_path)

    def exists_rel(self, rel_path: str) -> bool:
        """Return True if a relative path exists on disk."""
        if not rel_path or not isinstance(rel_path, str):
            return False
        return os.path.exists(self.abs_path(rel_path))

    def _make_path(self, category: str, extension: str, recording_id: str = None) -> str:
        now = datetime.datetime.utcnow()
        if recording_id is None:
            recording_id = uuid.uuid4().hex[:12]
    
        rel_dir = f"{category}"
        os.makedirs(self.abs_path(rel_dir), exist_ok=True)
    
        filename = f"{now:%Y%m%d_%H%M%S}_{recording_id}.{extension}"
        return Path(rel_dir, filename).as_posix()

    # ---------------- READ / WRITE ---------------- #

    def save_upload(self, filename: str, file_bytes: bytes):
        now = datetime.datetime.utcnow()
        recording_id = uuid.uuid4().hex[:12]
    
        rel_dir = f"audio/{recording_id}"  # <-- per recording
        os.makedirs(self.abs_path(rel_dir), exist_ok=True)
    
        safe_name = os.path.basename(filename).replace(" ", "_")
        final_name = f"{now:%Y%m%d_%H%M%S}_{recording_id}_{safe_name}"
    
        rel_path = Path(rel_dir, final_name).as_posix()
        abs_path = self.abs_path(rel_path)
    
        with open(abs_path, "wb") as f:
            f.write(file_bytes)
    
        return recording_id, rel_path

    def save_transcript(self, recording_id: str, text: str, version: str = "original") -> str:
        rel_path = f"transcripts/{recording_id}/{version}.txt"
        abs_path = self.abs_path(rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(text)

        return Path(rel_path).as_posix()

    def save_words(self, recording_id: str, words: list, version: str = "original") -> str:
        """
        Save per-word tokens (with timing + prob) as JSON.
        Keep it versioned because edited != original.
        """
        rel_path = f"transcripts/{recording_id}/aligned_words.json"

        # allow both dataclasses and dicts
        payload = []
        for w in (words or []):
            if isinstance(w, dict):
                payload.append(w)
            else:
                payload.append(getattr(w, "__dict__", {"value": str(w)}))

        return self.save_json(rel_path, payload)


    def load_text(self, rel_path: str) -> str:
        abs_path = self.abs_path(rel_path)
        with open(abs_path, "r", encoding="utf-8") as f:
            return f.read()

    def save_json(self, rel_path: str, data: Dict[str, Any]) -> str:
        rel_path = Path(rel_path).as_posix()
        abs_path = self.abs_path(rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    
        tmp_path = abs_path + ".tmp"
    
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
        os.replace(tmp_path, abs_path)
        return rel_path

    def load_json(self, rel_path: str) -> Dict[str, Any]:
        abs_path = self.abs_path(rel_path)
        with open(abs_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_segments(self, recording_id: str, segments: list) -> str:
        rel_path = f"segments/{recording_id}/{recording_id}.json"
        data = {"segments": [s.__dict__ for s in segments]}
        return self.save_json(rel_path, data)

    # ---------------- METADATA ---------------- #

    def load_metadata(self, recording_id: str) -> Dict[str, Any]:
        rel_path = f"metadata/{recording_id}.json"
        abs_path = self.abs_path(rel_path)

        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"No metadata for recording {recording_id}")

        with open(abs_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_metadata(self, recording_id: str, metadata: Dict[str, Any]) -> str:
        rel_path = f"metadata/{recording_id}.json"
        abs_path = self.abs_path(rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    
        tmp_path = abs_path + ".tmp"
    
        from dataclasses import is_dataclass, asdict
    
        def _json_default(o):
            if is_dataclass(o):
                return asdict(o)
            try:
                import numpy as np
                if isinstance(o, (np.integer, np.floating)):
                    return o.item()
            except Exception:
                pass
            if hasattr(o, "__dict__"):
                return o.__dict__
            return str(o)
    
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=_json_default)
    
        os.replace(tmp_path, abs_path)
        return Path(rel_path).as_posix()


    # ---------------- LEGACY / OPTIONAL ---------------- #
    # These are not aligned with your current "metadata keyed by recording_id" approach.
    # Keep only if you really still use them.

    def link_objects(self, audio_path: str, transcript_path: str = None, summary_path: str = None) -> str:
        metadata = {
            "audio": audio_path,
            "transcript": transcript_path,
            "summary": summary_path,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

        meta_dir = self.abs_path("metadata")
        os.makedirs(meta_dir, exist_ok=True)

        meta_filename = f"{uuid.uuid4().hex[:12]}_meta.json"
        meta_rel = Path("metadata", meta_filename).as_posix()
        meta_abs = self.abs_path(meta_rel)

        with open(meta_abs, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        return meta_rel

    def list_recordings(self) -> list:
        """
        Legacy helper: scans audio directory directly (may include orphans).
        Prefer scanning metadata directory for real "recordings".
        """
        audio_dir = self.abs_path("audio")
        recordings = []
        for root, _, files in os.walk(audio_dir):
            for f in files:
                if f.lower().endswith((".wav", ".mp3", ".m4a", ".webm")):
                    recordings.append(os.path.join(root, f))
        return recordings

    # ---------------- DELETION ---------------- #

    def delete_transcript(self, recording_id: str, version: str) -> bool:
        meta = self.load_metadata(recording_id)
        rel = (meta.get("transcripts") or {}).get(version)
        if not rel:
            return False
    
        abs_path = self.abs_path(rel)
        if os.path.exists(abs_path):
            os.remove(abs_path)
            self._prune_empty_parents(os.path.dirname(abs_path), stop_at=self.base)
    
        meta.setdefault("transcripts", {})
        meta["transcripts"][version] = None
        self.save_metadata(recording_id, meta)
        return True

    def delete_audio(self, recording_id: str) -> bool:
        meta = self.load_metadata(recording_id)
        audio_rel = meta.get("audio")
        if not audio_rel:
            return False
    
        audio_abs = self.abs_path(audio_rel)
        if os.path.exists(audio_abs):
            os.remove(audio_abs)
            self._prune_empty_parents(os.path.dirname(audio_abs), stop_at=self.base)
    
        meta["audio"] = None
        self.save_metadata(recording_id, meta)
        return True

    def delete_recording(self, recording_id: str) -> bool:
        for rel_dir in [
            f"audio/{recording_id}",
            f"transcripts/{recording_id}",
            f"segments/{recording_id}",
        ]:
            abs_dir = self.abs_path(rel_dir)
            if os.path.isdir(abs_dir):
                shutil.rmtree(abs_dir, ignore_errors=True)
    
        meta_abs = self.abs_path(f"metadata/{recording_id}.json")
        if os.path.exists(meta_abs):
            os.remove(meta_abs)
    
        self._prune_empty_parents(self.abs_path("audio"), stop_at=self.base)
        self._prune_empty_parents(self.abs_path("transcripts"), stop_at=self.base)
        self._prune_empty_parents(self.abs_path("segments"), stop_at=self.base)
        self._prune_empty_parents(self.abs_path("metadata"), stop_at=self.base)
    
        return True

    @staticmethod
    def _prune_empty_parents(abs_path: str, stop_at: str):
        """
        Remove empty parent folders up to stop_at (exclusive).
        stop_at should be an absolute path (e.g. DATA_DIR).
        """
        stop_at = os.path.abspath(stop_at)
        cur = os.path.abspath(abs_path)
    
        while True:
            if cur == stop_at:
                return
            if not os.path.isdir(cur):
                cur = os.path.dirname(cur)
                continue
            try:
                if os.listdir(cur):
                    return
                os.rmdir(cur)
            except OSError:
                return
            cur = os.path.dirname(cur)
