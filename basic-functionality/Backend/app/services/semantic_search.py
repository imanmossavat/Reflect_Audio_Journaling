from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import os
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.config import settings
from app.services.storage import StorageManager


@dataclass
class SemanticHit:
    recording_id: str
    segment_id: int
    score: float
    label: str
    text: str
    start_s: Optional[float] = None
    end_s: Optional[float] = None


from app.core.logging_config import logger

class SemanticSearchManager:
    """
    Simple semantic search over stored segments (latest segments file per recording).
    No vector DB. Just encode + cosine.
    """

    def __init__(self, storage: Optional[StorageManager] = None):
        model_name = getattr(settings, "SEMANTIC_SEARCH_MODEL", "all-mpnet-base-v2")
        logger.info(f"Initializing SemanticSearchManager with model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.store = storage or StorageManager()

    def search(
        self,
        query: str,
        top_k: int = 8,
        min_score: float = 0.25,
        per_recording_cap: int = 2,
    ) -> List[SemanticHit]:
        q = (query or "").strip()
        if not q:
            return []

        # load all recordings metadata
        meta_dir = self.store.abs_path("metadata")
        if not os.path.isdir(meta_dir):
            return []

        # gather candidates
        candidates: List[Tuple[str, Dict[str, Any]]] = []
        for fn in os.listdir(meta_dir):
            if not fn.endswith(".json"):
                continue
            rec_id = fn[:-5]
            try:
                meta = self.store.load_metadata(rec_id) or {}
            except Exception:
                continue

            seg_paths = meta.get("segments", []) or []
            if not seg_paths:
                continue

            try:
                payload = self.store.load_json(seg_paths[-1])  # latest
                segs = payload.get("segments", []) if isinstance(payload, dict) else []
            except Exception:
                continue

            for seg in segs:
                # segment text
                text = (seg.get("text") or "").strip()
                if not text:
                    continue
                candidates.append((rec_id, seg))

        if not candidates:
            return []

        texts = [seg["text"] for _, seg in candidates]

        q_emb = self.model.encode([q], convert_to_numpy=True)
        s_emb = self.model.encode(texts, convert_to_numpy=True, batch_size=16)

        sims = cosine_similarity(q_emb, s_emb)[0]  # shape: (N,)

        # build hits
        hits: List[SemanticHit] = []
        for i, score in enumerate(sims):
            if float(score) < float(min_score):
                continue
            rec_id, seg = candidates[i]
            hits.append(
                SemanticHit(
                    recording_id=rec_id,
                    segment_id=int(seg.get("id", 0)),
                    score=float(score),
                    label=str(seg.get("label") or ""),
                    text=str(seg.get("text") or ""),
                    start_s=seg.get("start_s"),
                    end_s=seg.get("end_s"),
                )
            )

        # sort + cap
        hits.sort(key=lambda h: h.score, reverse=True)

        out: List[SemanticHit] = []
        per_rec = {}
        for h in hits:
            c = per_rec.get(h.recording_id, 0)
            if c >= per_recording_cap:
                continue
            out.append(h)
            per_rec[h.recording_id] = c + 1
            if len(out) >= top_k:
                break

        return out
