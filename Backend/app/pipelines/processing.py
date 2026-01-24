from __future__ import annotations

from app.analysis.speech import analyze_words

import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.domain.models import PiiFinding, Recording
from app.core.logging_config import logger
import os

# =============================================================================
# Helpers
# =============================================================================

def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fallback_title(created_at_iso: str) -> str:
    try:
        dt = datetime.fromisoformat(created_at_iso.replace("Z", "+00:00"))
        return dt.strftime("Recording · %Y-%m-%d %H:%M")
    except Exception:
        return "Recording"


def redact_text(text: str, hits, pii_service: PIIDetector) -> str:
    if hasattr(pii_service, "redact_with_labels"):
        return pii_service.redact_with_labels(text, hits)
    return pii_service.redact(text, hits)


def transcript_from_text(recording_id: str, text: str):
    sentences = [
        {
            "id": i,
            "start_s": None,
            "end_s": None,
            "text": s.strip(),
        }
        for i, s in enumerate(re.split(r"(?<=[.!?])\s+", text.strip()))
        if s.strip()
    ]

    return type(
        "Transcript",
        (),
        {
            "recording_id": recording_id,
            "text": text,
            "sentences": sentences,
        },
    )


def first_segment_label(segments) -> Optional[str]:
    if not segments:
        return None
    first = segments[0]
    label = getattr(first, "label", None)
    if isinstance(label, str) and label.strip():
        return label.strip()
    return None


# =============================================================================
# Pipelines
# =============================================================================

def process_uploaded_audio(
    filename: str, 
    file_bytes: bytes, 
    storage: StorageManager,
    transcriber: TranscriptionManager,
    pii_service: PIIDetector,
    language: str = "en"
) -> Dict[str, Any]:
    rec_id, audio_rel = storage.save_upload(filename, file_bytes)
    audio_abs = storage.abs_path(audio_rel)

    rec = Recording(id=rec_id, path=audio_abs, language=language)
    
    try:
        import librosa
        if os.path.exists(audio_abs):
            dur = librosa.get_duration(path=audio_abs)
            rec.duration_s = float(dur)
    except Exception:
        rec.duration_s = 0.0

    created_at = now_utc_iso()

    transcript = transcriber.transcribe(rec)
    if not transcript or not transcript.text:
        raise RuntimeError("Transcription failed")
    
    original_text = transcript.text
    
    words_path = None
    if getattr(transcript, "words", None):
        words_path = storage.save_words(
            recording_id=rec_id,
            words=transcript.words,
            version="original",
        )

    speech = {}
    try:
        if words_path and storage.exists_rel(words_path):
            aligned_words = storage.load_json(words_path)
            speech = analyze_words(aligned_words, language_code=language, confidence_threshold=0.7)
    except Exception:
        speech = {}

    pii_hits_original = pii_service.detect(transcript)
    redacted_text_original = redact_text(original_text, pii_hits_original, pii_service)

    original_path = storage.save_transcript(rec_id, original_text, version="original")
    redacted_path = storage.save_transcript(rec_id, redacted_text_original, version="redacted")

    metadata = {
        "recording_id": rec_id,
        "audio": audio_rel,
        "language": language,
        "source": "audio",
        "created_at": created_at,
        "duration": rec.duration_s,
        "aligned_words": words_path,
        "speech": speech,
        "title": fallback_title(created_at),
        "tags": [],

        "transcripts": {
            "original": original_path,
            "edited": None,
            "redacted": redacted_path,
        },

        "segments": [],        
        "prosody": [],

        "sentences": [s.__dict__ for s in (getattr(transcript, "sentences", None) or [])],
        "pii_original": [p.__dict__ for p in pii_hits_original],
        "pii_edited": [],
        "pii": [p.__dict__ for p in pii_hits_original],
    }

    storage.save_metadata(rec_id, metadata)

    return {
        "recording_id": rec_id,
        "transcript": {"text": original_text},
        "pii": [p.__dict__ for p in pii_hits_original],
    }

def process_after_edit(
    recording_id: str, 
    edited_text: str,
    storage: StorageManager,
    segmenter: SegmentationManager,
    pii_service: PIIDetector,
    prosody_service: ProsodyManager,
    transcriber: TranscriptionManager,
) -> Dict[str, Any]:
    """
    After user edits:
    - Save edited transcript
    - Segment edited transcript
    - Detect PII on edited text AND preserve existing manual tags
    - Save redacted edited transcript (including manual tags)
    - Compute prosody
    - Update metadata
    """
    edited_text = (edited_text or "").strip()
    if not edited_text:
        raise RuntimeError("Edited transcript is empty")

    # 1. Load existing metadata
    meta = storage.load_metadata(recording_id) or {}
    meta.setdefault("transcripts", {})
    meta.setdefault("segments", [])
    meta.setdefault("sentences", [])

    # 2. Save the edited transcript
    edited_path = storage.save_transcript(recording_id, edited_text, version="edited")
    edited_transcript_obj = transcript_from_text(recording_id, edited_text)

    # 3. Handle Segmentation
    segments = segmenter.segment(edited_transcript_obj, recording_id=recording_id)

    # --- Map segments to time intervals from original sentences ---
    timed_sentences = [s for s in (meta.get("sentences") or []) if isinstance(s, dict)]
    sent_time = {}
    for s in timed_sentences:
        sid = s.get("id")
        if sid is None: continue
        sent_time[int(sid)] = (s.get("start_s"), s.get("end_s"))

    sentence_to_segment = {}
    for seg in segments:
        sids = getattr(seg, "sentence_ids", None) or []
        for sid in sids:
            try: sentence_to_segment[int(sid)] = int(seg.id)
            except: pass

    for seg in segments:
        sids = getattr(seg, "sentence_ids", None) or []
        sids = [int(x) for x in sids if isinstance(x, (int, float, str))]
        starts = []
        ends = []
        for sid in sids:
            t = sent_time.get(sid)
            if not t: continue
            st, en = t
            if st is not None: starts.append(float(st))
            if en is not None: ends.append(float(en))
        seg.start_s = min(starts) if starts else None
        seg.end_s = max(ends) if ends else None


    # 4. Save segments and cleanup old paths
    new_segments_path = storage.save_segments(recording_id, segments)
    old_seg_paths = list(meta.get("segments", []) or [])
    for rel in old_seg_paths:
        if not rel or rel == new_segments_path: continue
        abs_path = storage.abs_path(rel)
        if os.path.exists(abs_path): os.remove(abs_path)
    meta["segments"] = [new_segments_path]

    # --- 5. PII PERSISTENCE ---

    # Run fresh AI detection
    new_ai_hits = pii_service.detect(edited_transcript_obj)

    # Harvest existing manual hits from current metadata
    # We look in pii_edited because that's where manual tags were stored
    current_pii_edited = meta.get("pii_edited", []) or []
    manual_pii_dicts = [hit for hit in current_pii_edited if hit.get("label") == "MANUAL"]

    # Convert manual dicts back to PiiFinding objects so redact_text can use them
    manual_pii_objs = [PiiFinding(**m) for m in manual_pii_dicts]

    # Combine AI + Manual for the "Edited" state
    all_hits_for_redaction = new_ai_hits + manual_pii_objs

    # Redact using combined AI and manual hits
    redacted_text_edited = redact_text(edited_text, all_hits_for_redaction, pii_service)
    redacted_path = storage.save_transcript(recording_id, redacted_text_edited, version="redacted")

    # --- 6. PROSODY ANALYSIS ---
    prosody_features = []
    try:
        audio_rel = meta.get("audio")
        if audio_rel and timed_sentences:
            audio_abs = storage.abs_path(audio_rel)
            audio_array = transcriber._load_audio_ffmpeg(audio_abs, sr=16000)
            from app.domain.models import Sentence
            sentence_objs = []
            for s in timed_sentences:
                sid, st, en, txt = s.get("id"), s.get("start_s"), s.get("end_s"), str(s.get("text", "")).strip()
                if sid is None or st is None or en is None: continue
                sentence_objs.append(Sentence(id=int(sid), start_s=float(st), end_s=float(en), text=txt, meta=s.get("meta")))

            if sentence_objs:
                timed_transcript_obj = type("Transcript", (), {"recording_id": recording_id, "text": edited_text, "sentences": sentence_objs})
                prosody_features = prosody_service.analyze_sentences(timed_transcript_obj, audio_array)
                for pf in prosody_features or []:
                    sid = getattr(pf, "sentence_id", None)
                    if sid is not None: pf.segment_id = sentence_to_segment.get(int(sid))
    except Exception:
        prosody_features = []

    # --- 7. FINAL METADATA UPDATE ---
    meta["transcripts"]["edited"] = edited_path
    meta["transcripts"]["redacted"] = redacted_path

    # Ensure pii_original exists as a frozen snapshot of the first AI pass
    if "pii_original" not in meta:
        meta["pii_original"] = meta.get("pii", []) or []

    # Save the merged list (AI hits converted to dict + the manual dicts we harvested)
    merged_pii_dicts = [p.__dict__ for p in new_ai_hits] + manual_pii_dicts

    meta["pii_edited"] = merged_pii_dicts
    meta["pii"] = merged_pii_dicts
    meta["prosody"] = [p.__dict__ for p in (prosody_features or [])]

    # Handle Title
    cur_title = (meta.get("title") or "").strip()
    if not cur_title or cur_title.startswith("Recording ·"):
        seg_title = first_segment_label(segments)
        if seg_title: meta["title"] = seg_title

    storage.save_metadata(recording_id, meta)

    return {
        "recording_id": recording_id,
        "segments": [s.__dict__ for s in segments],
        "prosody": [p.__dict__ for p in (prosody_features or [])],
        "pii_edited": merged_pii_dicts,
        "status": "saved",
    }

def process_text_entry(
    text: str, 
    storage: StorageManager,
    segmenter: SegmentationManager,
    pii_service: PIIDetector,
    title: Optional[str] = None, 
    tags: Optional[List[str]] = None, 
    language: str = "en", 
    run_segmentation: bool = True, 
    run_pii: bool = True
) -> Dict[str, Any]:
    import uuid
    recording_id = uuid.uuid4().hex
    text = (text or "").strip()
    if not text:
        raise RuntimeError("Text entry is empty")

    original_path = storage.save_transcript(recording_id, text, version="original")

    meta = {
        "recording_id": recording_id,
        "created_at": now_utc_iso(),
        "title": (title or "").strip() or None,
        "tags": tags or [],
        "language": language,
        "source": "text",
        "audio": None,
        "transcripts": {"original": original_path, "edited": None, "redacted": None},
        "segments": [],
        "pii": [],
        "pii_original": [],
        "pii_edited": [],
        "duration": (len(text.split()) / 150.0) * 60.0  # Estimate: 150 words per minute
    }

    if run_segmentation:
        try:
            fake_transcript = transcript_from_text(recording_id, text)
            segs = segmenter.segment(transcript=fake_transcript, recording_id=recording_id)
            if not meta.get("title") and segs:
                meta["title"] = first_segment_label(segs)
            meta["segments"] = [storage.save_segments(recording_id, segs)]
        except Exception:
            logger.exception("Segmentation failed for text recording")

    if run_pii:
        try:
            hits = pii_service.detect(transcript_from_text(recording_id, text))
            meta["pii"] = [p.__dict__ for p in hits]
            meta["pii_original"] = meta["pii"]
        except Exception:
            logger.exception("PII detection failed for text recording")

    storage.save_metadata(recording_id, meta)
    return {"status": "ok", "recording_id": recording_id}
