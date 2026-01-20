import re
import spacy

from app.domain.models import PiiFinding
from app.core.config import settings

from typing import List, Any

class PIIDetector:
    """
    Detects and optionally redacts Personally Identifiable Information (PII)
    using regex patterns and spaCy's Named Entity Recognition.
    """

    def __init__(self):
        self.language = settings.LANGUAGE
        self.nlp = spacy.load(f"{settings.LANGUAGE}_core_web_sm")
        self.patterns = settings.pii_patterns

    # ---------------- PUBLIC METHODS ---------------- #

    def detect(self, transcript):
        """
        Detect PII inside a transcript object.
        Returns a list of PiiFinding domain objects.
        """
        text = transcript.text
        findings = []

        # --- Regex-based detection --- #
        for label, pattern in self.patterns.items():
            for match in re.finditer(pattern, text):
                findings.append(
                    PiiFinding(
                        recording_id=transcript.recording_id,
                        start_char=match.start(),
                        end_char=match.end(),
                        label=label,
                        preview=match.group(),
                    )
                )

        # --- spaCy NER-based detection --- #
        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ in ["PERSON", "GPE", "ORG", "LOC", "DATE", "MONEY"]:
                findings.append(
                    PiiFinding(
                        recording_id=transcript.recording_id,
                        start_char=ent.start_char,
                        end_char=ent.end_char,
                        label=ent.label_,
                        preview=ent.text,
                    )
                )

        # --- Deduplicate overlapping entities --- #
        unique = []
        seen = set()

        for f in findings:
            key = (int(f.start_char), int(f.end_char), f.label)
            if key in seen:
                continue
            seen.add(key)
            unique.append(f)

        return unique

    @staticmethod
    def redact(text: str, findings: List[PiiFinding]) -> str:
        """
        Replace detected PII spans with REDACTED:<LABEL>.
        Uses start_char/end_char from findings.
        """
        if not text or not findings:
            return text
    
        # normalize + sort
        spans = sorted(
            [
                {
                    "start": int(f.start_char),
                    "end": int(f.end_char),
                    "label": f.label or "PII",
                }
                for f in findings
                if f.start_char is not None and f.end_char is not None
            ],
            key=lambda s: (s["start"], s["end"]),
        )
    
        # merge overlapping spans
        merged = []
        for s in spans:
            if not merged:
                merged.append(
                    {"start": s["start"], "end": s["end"], "labels": {s["label"]}}
                )
                continue
    
            last = merged[-1]
            if s["start"] > last["end"]:
                merged.append(
                    {"start": s["start"], "end": s["end"], "labels": {s["label"]}}
                )
            else:
                last["end"] = max(last["end"], s["end"])
                last["labels"].add(s["label"])
    
        # build redacted output
        out = []
        cursor = 0
        n = len(text)
    
        for m in merged:
            start = max(0, min(n, m["start"]))
            end = max(0, min(n, m["end"]))
            if end <= start:
                continue
    
            # text before span
            if start > cursor:
                out.append(text[cursor:start])
    
            # label token
            label = (
                next(iter(m["labels"]))
                if len(m["labels"]) == 1
                else "+".join(sorted(m["labels"]))
            )
            out.append(f"[REDACTED:{label}]")
    
            cursor = end
    
        # tail
        if cursor < n:
            out.append(text[cursor:])
    
        return "".join(out)

