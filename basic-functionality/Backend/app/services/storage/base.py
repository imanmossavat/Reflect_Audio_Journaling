import os
import json
from pathlib import Path
from typing import Any, Dict, Optional
from app.core.config import settings
from app.core.logging_config import logger

class FileEngine:
    """
    Provides filesystem operations for the storage layer.
    Manages path resolution and basic I/O within settings.DATA_DIR.
    """

    def __init__(self, base_dir: Optional[str] = None):
        self.base = base_dir or settings.DATA_DIR
        os.makedirs(self.base, exist_ok=True)
        logger.info(f"FileEngine initialized at: {self.base}")

    def abs_path(self, rel_path: str) -> str:
        return os.path.join(self.base, rel_path)

    def exists(self, rel_path: str) -> bool:
        if not rel_path or not isinstance(rel_path, str):
            return False
        return os.path.exists(self.abs_path(rel_path))

    def read_text(self, rel_path: str) -> str:
        with open(self.abs_path(rel_path), "r", encoding="utf-8") as f:
            return f.read()

    def write_text(self, rel_path: str, text: str):
        path = self.abs_path(rel_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def write_bytes(self, rel_path: str, data: bytes):
        path = self.abs_path(rel_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)

    def read_json(self, rel_path: str) -> Dict[str, Any]:
        with open(self.abs_path(rel_path), "r", encoding="utf-8") as f:
            return json.load(f)

    def write_json(self, rel_path: str, data: Any):
        path = self.abs_path(rel_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp_path = path + ".tmp"
        
        # Helper for dataclasses and numpy items
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
            json.dump(data, f, indent=2, ensure_ascii=False, default=_json_default)
        
        os.replace(tmp_path, path)

    def delete_file(self, rel_path: str):
        path = self.abs_path(rel_path)
        if os.path.exists(path):
            os.remove(path)
            self.prune_empty_dirs(os.path.dirname(path))

    def prune_empty_dirs(self, abs_path: str):
        """Remove empty parent folders up to base_dir."""
        stop_at = os.path.abspath(self.base)
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
                logger.debug(f"Pruned empty directory: {cur}")
            except OSError:
                return
            cur = os.path.dirname(cur)
