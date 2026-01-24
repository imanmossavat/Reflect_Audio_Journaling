import os
import logging
from typing import List, Optional, Dict, Any
from app.services.storage import StorageManager
from app.core.config import settings

from app.core.logging_config import logger

class RecordingService:
    def __init__(self, storage: StorageManager):
        self.store = storage

    def list_recordings(self) -> List[Dict[str, Any]]:
        items = []
        meta_dir = os.path.join(settings.DATA_DIR, "metadata")

        if not os.path.isdir(meta_dir):
            return []

        for meta_file in os.listdir(meta_dir):
            if not meta_file.endswith(".json"):
                continue

            rec_id = meta_file[:-5]
            try:
                meta = self.store.load_metadata(rec_id) or {}
                t = meta.get("transcripts", {}) or {}
                latest = self._pick_latest_version(t)

                search_text = ""
                if latest:
                    rel = self._get_transcript_rel_path(rec_id, t, latest)
                    search_text = self._safe_load_text(rel)

                MAX_CHARS = 4000
                if len(search_text) > MAX_CHARS:
                    search_text = search_text[:MAX_CHARS]


                pii_list = meta.get("pii", [])
                pii_types = {}
                for p in pii_list:
                    label = p.get("label", "UNKNOWN")
                    pii_types[label] = pii_types.get(label, 0) + 1

                items.append({
                    "recording_id": rec_id,
                    "title": meta.get("title"),
                    "tags": meta.get("tags", []),
                    "created_at": meta.get("created_at"),
                    "has_audio": bool(meta.get("audio")),
                    "transcripts": {
                        "original": self._has_transcript(t, "original"),
                        "edited": self._has_transcript(t, "edited"),
                        "redacted": self._has_transcript(t, "redacted"),
                    },
                    "latest_transcript_version": latest,
                    "search_text": search_text,
                    "speech": meta.get("speech", {}),
                    "duration": meta.get("duration", 0),
                    "pii_summary": pii_types
                })
            except Exception as e:
                logger.warning(f"Error loading metadata for {rec_id}: {e}")
                continue

        items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        return items

    def get_recording_full(self, recording_id: str) -> Optional[Dict[str, Any]]:
        try:
            meta = self.store.load_metadata(recording_id)
            if meta is None:
                return None
        except FileNotFoundError:
            return None

        t = meta.get("transcripts", {}) or {}
        chosen_version = "edited" if t.get("edited") else ("original" if t.get("original") else ("redacted" if t.get("redacted") else None))

        transcript_text = ""
        transcript_version = None
        if chosen_version:
            rel = self._get_transcript_rel_path(recording_id, t, chosen_version)
            transcript_text = self._safe_load_text(rel)
            transcript_version = chosen_version

        segments = []
        seg_paths = meta.get("segments", []) or []
        if seg_paths:
            try:
                payload = self.store.load_json(seg_paths[-1])
                segments = payload.get("segments", [])
            except Exception:
                segments = []

        aligned_words = []
        rel = meta.get("aligned_words")
        if rel and self.store.exists_rel(rel):
            aligned_words = self.store.load_json(rel)

        return {
            "recording_id": recording_id,
            "audio_url": f"/api/audio/{recording_id}",
            "title": meta.get("title"),
            "tags": meta.get("tags", []),
            "transcript": transcript_text,
            "transcript_version": transcript_version,
            "prosody": meta.get("prosody", []),
            "aligned_words": aligned_words,
            "segments": segments,
            "pii": meta.get("pii", []),
            "pii_original": meta.get("pii_original", meta.get("pii", [])),
            "pii_edited": meta.get("pii_edited", []),
            "created_at": meta.get("created_at"),
            "transcripts": t,
            "has_audio": bool(meta.get("audio")),
            "sentences": meta.get("sentences", []),
            "speech": meta.get("speech", {})
        }

    # --- HELPERS ---

    def _pick_latest_version(self, t: dict) -> Optional[str]:
        if not isinstance(t, dict): return None
        if t.get("edited"): return "edited"
        if t.get("redacted"): return "redacted"
        if t.get("original"): return "original"
        return None

    def _get_transcript_rel_path(self, recording_id: str, t: dict, version: str) -> Optional[str]:
        if not version: return None
        val = (t or {}).get(version)
        if isinstance(val, str) and val.strip(): return val
        if val is True: return f"transcripts/{recording_id}/{version}.txt"
        return None

    def _safe_load_text(self, rel_path: Optional[str]) -> str:
        if not rel_path or not self.store.exists_rel(rel_path): return ""
        try:
            return self.store.load_text(rel_path) or ""
        except Exception:
            return ""

    def _has_transcript(self, t: dict, version: str) -> bool:
        v = (t or {}).get(version)
        if isinstance(v, bool): return v
        if isinstance(v, str): return bool(v.strip()) and self.store.exists_rel(v)
        return False
