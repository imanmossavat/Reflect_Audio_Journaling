# app/analysis/speech.py
from __future__ import annotations

import re
from typing import Any, Dict, List

import numpy as np


# -----------------------------------------------------------------------------
# Token cleaning
# -----------------------------------------------------------------------------

_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
_WS_RE = re.compile(r"\s+")

def _norm_token(s: str) -> str:
    s = (s or "").strip().lower()
    s = _PUNCT_RE.sub("", s)
    s = _WS_RE.sub(" ", s)
    return s

# -----------------------------------------------------------------------------
# Filler patterns (token sequences)
# -----------------------------------------------------------------------------

_FILLERS_EN: List[List[str]] = [
    ["to", "be", "honest"],
    ["kind", "of"],
    ["um"],
    ["ah"],
    ["huh"],
    ["and", "so"],
    ["so", "um"],
    ["uh"],
    ["and", "um"],
    ["like", "um"],
    ["so", "like"],
    ["like", "it's"],
    ["it's", "like"],
    ["i", "mean"],
    ["yeah"],
    ["ok", "so"],
    ["uh", "so"],
    ["so", "uh"],
    ["yeah", "so"],
    ["you", "know"],
    ["it's", "uh"],
    ["uh", "and"],
    ["and", "uh"],
    ["like"],
    ["kind"],
    ["well"],
    ["actually"],
    ["basically"],
    ["literally"],
    ["you", "see"],
    ["right"],
    ["so"],
    ["okay"],
    ["alright"],
    ["you", "know", "what", "i", "mean"],
    ["i", "guess"],
    ["i", "think"],
    ["anyway"],
    ["just"],
    ["so", "yeah"],
    ["so", "okay"],
    ["umm"],
    ["hmm"],
]

_FILLERS_NL: List[List[str]] = [
    ["eh"],
    ["uh"],
    ["uuh"],
    ["uhm"],
    ["euh"],
    ["zeg", "maar"],
    ["weet", "je"],
    ["dus"],
    ["nou"],
    ["toch"],
    ["zeg", "maar", "even"],
    ["eigenlijk"],
    ["soort", "van"],
    ["om", "het", "zo", "te", "zeggen"],
    ["weet", "je", "wel"],
    ["ja"],
    ["oké"],
    ["nou", "ja"],
    ["hè"],
    ["inderdaad"],
    ["juist"],
    ["precies"],
    ["dus", "ja"],
    ["maar", "ja"],
    ["zeg"],
    ["ehm"],
    ["hm"],
    ["ok"],
    ["oké", "dan"],
]


# -----------------------------------------------------------------------------
# Pause statistics (from aligned word timestamps)
# -----------------------------------------------------------------------------

def pause_stats(words: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute pause/silence statistics from aligned word timestamps.

    Expects each word dict like:
      {
        "word": "atmosphere.",
        "start_s": 42.932,
        "end_s": 44.313,
        "prob": 0.543
      }
    """
    pauses: List[float] = []
    total_silence = 0.0

    for i in range(1, len(words)):
        prev_end = words[i - 1].get("end_s")
        curr_start = words[i].get("start_s")

        if prev_end is None or curr_start is None:
            continue

        pause = float(curr_start) - float(prev_end)
        if pause > 0:
            pauses.append(pause)
            total_silence += pause

    return {
        "avg_pause_s": float(np.mean(pauses)) if pauses else 0.0,
        "max_pause_s": float(np.max(pauses)) if pauses else 0.0,
        "total_silence_s": float(total_silence),
        "pause_count": int(len(pauses)),
    }


# -----------------------------------------------------------------------------
# Confidence statistics (from prob)
# -----------------------------------------------------------------------------

def confidence_stats(
    words: List[Dict[str, Any]],
    threshold: float = 0.7,
    low_cap: int = 50,
) -> Dict[str, Any]:
    """
    Summarize per-word confidence probabilities (prob).
    Flags words below threshold.
    """
    probs: List[float] = []
    low: List[Dict[str, Any]] = []

    for w in words:
        p = w.get("prob")
        if p is None:
            continue

        p = float(p)
        probs.append(p)

        if p < threshold:
            low.append({
                "word": (w.get("word") or "").strip(),
                "prob": p,
                "start_s": w.get("start_s"),
                "end_s": w.get("end_s"),
            })

    if not probs:
        return {
            "mean": None,
            "median": None,
            "min": None,
            "max": None,
            "std": None,
            "count": 0,
            "threshold": float(threshold),
            "low_count": 0,
            "low": [],
        }

    arr = np.asarray(probs, dtype=float)

    return {
        "mean": float(arr.mean()),
        "median": float(np.median(arr)),
        "min": float(arr.min()),
        "max": float(arr.max()),
        "std": float(arr.std()),
        "count": int(arr.size),
        "threshold": float(threshold),
        "low_count": int(len(low)),
        "low": low[:low_cap],
    }


# -----------------------------------------------------------------------------
# Filler detection
# -----------------------------------------------------------------------------

def filler_stats(words: List[Dict[str, Any]], language_code: str = "en") -> Dict[str, Any]:
    """
    Detect filler words/phrases from aligned word tokens.

    Uses greedy, non-overlapping matching against a small list of patterns.
    """
    patterns = _FILLERS_NL if (language_code or "").startswith("nl") else _FILLERS_EN

    toks: List[str] = []
    for w in words:
        t = _norm_token(w.get("word") or "")
        if t:
            toks.append(t)

    hits: List[Dict[str, Any]] = []
    i = 0

    while i < len(toks):
        matched = False
        for pat in patterns:
            n = len(pat)
            if i + n <= len(toks) and toks[i:i + n] == pat:
                hits.append({"phrase": " ".join(pat), "index": i})
                i += n
                matched = True
                break
        if not matched:
            i += 1

    count = len(hits)
    pct = (count / len(toks)) * 100 if toks else 0.0

    return {
        "count": count,
        "percent": float(pct),
        "hits": hits,
    }


# -----------------------------------------------------------------------------
# Public wrapper
# -----------------------------------------------------------------------------

def analyze_words(
    words: List[Dict[str, Any]],
    language_code: str = "en",
    confidence_threshold: float = 0.7,
) -> Dict[str, Any]:
    """
    Compute transcript-level speech stats from aligned words.
    Returns one summary for the whole transcript (not per sentence/segment).
    """
    words = words or []

    return {
        "pause": pause_stats(words),
        "fillers": filler_stats(words, language_code=language_code),
        "confidence": confidence_stats(words, threshold=confidence_threshold),
    }