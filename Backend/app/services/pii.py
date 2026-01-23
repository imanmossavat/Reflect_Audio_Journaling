import re
import spacy

from app.domain.models import PiiFinding
from app.core.config import settings

from typing import List


class PIIDetector:
    def __init__(self):
        self.language = settings.LANGUAGE

        if self.language == "nl":
            model_name = "nl_core_news_lg"
        else:
            model_name = "en_core_web_trf"

        print(f"[PII] Initializing with installed model: {model_name}")

        try:
            self.nlp = spacy.load(model_name)
        except Exception as e:
            print(f"[PII] CRITICAL ERROR: Could not load {model_name}. "
                  f"Check if it's installed in your .venv. Error: {e}")
            self.nlp = spacy.blank(self.language)

        self.patterns = settings.PII_PATTERNS

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
        Sorts findings in REVERSE order to prevent index drift.
        """
        if not text or not findings:
            return text

        # 1. Convert to simple dicts and sort by start_char descending
        # Reversing is the key: changing text at index 100 
        # doesn't break a marker at index 10.
        items = []
        for f in findings:
            if f.start_char is not None and f.end_char is not None:
                items.append({
                    "start": int(f.start_char),
                    "end": int(f.end_char),
                    "label": f.label or "PII"
                })

        # Sort: Primary by start descending, secondary by end descending
        items.sort(key=lambda x: (x["start"], x["end"]), reverse=True)

        # 2. Merge overlaps (crucial for reverse redaction)
        merged = []
        for item in items:
            if not merged:
                merged.append(item)
                continue

            last = merged[-1]
            # If current item overlaps or touches the one we just added (which is later in text)
            if item["end"] >= last["start"]:
                # Extend the 'later' start to the 'earlier' start
                last["start"] = min(item["start"], last["start"])
                last["end"] = max(item["end"], last["end"])
                # Combine labels if they differ
                if item["label"] not in last["label"]:
                    last["label"] = f"{item['label']}+{last['label']}"
            else:
                merged.append(item)

        # 3. Apply redactions in reverse order
        redacted_text = text
        for m in merged:
            start = m["start"]
            end = m["end"]
            label = m["label"]

            # Simple string slicing: everything before + tag + everything after
            redacted_text = redacted_text[:start] + f"[REDACTED:{label}]" + redacted_text[end:]

        return redacted_text

