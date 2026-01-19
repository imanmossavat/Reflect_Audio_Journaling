import os
import uuid
import datetime
import json
from pathlib import Path
from typing import Any, Dict, Tuple

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
        return os.path.exists(self.abs_path(rel_path))

    def _make_path(self, category: str, extension: str, recording_id: str = None) -> str:
        now = datetime.datetime.utcnow()
        if recording_id is None:
            recording_id = uuid.uuid4().hex[:12]

        rel_dir = f"{category}/{now:%Y/%m/%d}"
        os.makedirs(self.abs_path(rel_dir), exist_ok=True)

        filename = f"{now:%Y%m%d_%H%M%S}_{recording_id}.{extension}"
        return Path(rel_dir, filename).as_posix()  # always forward slashes

    # ---------------- READ / WRITE ---------------- #

    def save_upload(self, filename: str, file_bytes: bytes) -> Tuple[str, str]:
        """
        Saves an uploaded audio file to the data directory.
        Returns (recording_id, rel_audio_path)
        """
        now = datetime.datetime.utcnow()
        recording_id = uuid.uuid4().hex[:12]

        rel_dir = f"audio/{now:%Y/%m/%d}"
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

    def load_text(self, rel_path: str) -> str:
        abs_path = self.abs_path(rel_path)
        with open(abs_path, "r", encoding="utf-8") as f:
            return f.read()

    def save_json(self, rel_path: str, data: Dict[str, Any]) -> str:
        rel_path = Path(rel_path).as_posix()
        abs_path = self.abs_path(rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        with open(abs_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return rel_path

    def load_json(self, rel_path: str) -> Dict[str, Any]:
        abs_path = self.abs_path(rel_path)
        with open(abs_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_segments(self, recording_id: str, segments: list) -> str:
        rel_path = self._make_path(f"segments/{recording_id}", "json", recording_id)
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

        with open(abs_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

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

        meta["audio"] = None
        self.save_metadata(recording_id, meta)
        return True

    def delete_recording(self, recording_id: str) -> bool:
        meta = self.load_metadata(recording_id)

        # audio (stored as rel path)
        ap = meta.get("audio")
        if ap:
            ap_abs = self.abs_path(ap)
            if os.path.exists(ap_abs):
                os.remove(ap_abs)

        # transcripts (stored as rel paths)
        for rel in (meta.get("transcripts") or {}).values():
            if rel:
                abs_path = self.abs_path(rel)
                if os.path.exists(abs_path):
                    os.remove(abs_path)

        # segments (stored as rel paths)
        for rel in (meta.get("segments") or []):
            if rel:
                abs_path = self.abs_path(rel)
                if os.path.exists(abs_path):
                    os.remove(abs_path)

        # metadata file
        meta_rel = f"metadata/{recording_id}.json"
        meta_abs = self.abs_path(meta_rel)
        if os.path.exists(meta_abs):
            os.remove(meta_abs)

        return True
