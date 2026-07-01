"""Document B §8's per-unit addressing: paragraph-boundary units for typed
entries, transcript-segment units for audio. A different granularity from
`chunking.py`'s semantic chunker (which exists for whole-document RAG
search) — units exist to be individually citable (`{{source_id:unit_id}}`,
Design Doc §6/Contract §5), not to be an optimal retrieval window.

`unit_id` is the item's index in its list (`p0`, `p1`, ... for paragraphs;
`s0`, `s1`, ... for transcript segments). Contract §8 describes audio units
as "exposing IDs that already exist" from WhisperX alignment — in practice
`Source.transcript_segments` stores `{text, start_s, end_s}` with no
carried-over id (see `sourceService._process_source_sync`), so the list
index is the closest stable proxy actually available; it holds because
transcript_segments is written once and never reordered.
"""
import re


def compute_units(text: str | None, transcript_segments: list | None) -> list[dict]:
    if transcript_segments:
        units = []
        for i, seg in enumerate(transcript_segments):
            seg_text = (seg.get("text") or "").strip()
            if seg_text:
                units.append({"unit_id": f"s{i}", "text": seg_text})
        return units

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]
    return [{"unit_id": f"p{i}", "text": p} for i, p in enumerate(paragraphs)]
