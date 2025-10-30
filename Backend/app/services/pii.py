import re
import spacy

from app.domain.models import PiiFinding
from app.core.config import settings

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

        # --- Regex-based detection ---
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

        # --- spaCy NER-based detection ---
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

        # --- Deduplicate overlapping entities ---
        unique = []
        seen = set()
        for f in findings:
            key = (f.label, f.preview)
            if key not in seen:
                seen.add(key)
                unique.append(f)

        return unique

    def redact(self, text: str) -> str:
        """
        Return a redacted version of text, replacing detected PII with [REDACTED].
        """
        doc = self.nlp(text)
        pii_entities = self.detect_from_text(text, doc)
        redacted = text
        for item in sorted(pii_entities, key=lambda x: x["start"], reverse=True):
            redacted = redacted[:item["start"]] + "[REDACTED]" + redacted[item["end"]:]
        return redacted

    # ---------------- PRIVATE HELPER ---------------- #

    def detect_from_text(self, text: str, doc=None):
        """
        Detect PII entities directly from a text string (used internally for redaction).
        """
        results = []
        # regex
        for label, pattern in self.patterns.items():
            for match in re.finditer(pattern, text):
                results.append({
                    "type": label,
                    "value": match.group(),
                    "start": match.start(),
                    "end": match.end()
                })

        # NER
        if doc is None:
            doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ in ["PERSON", "GPE", "ORG", "LOC", "DATE", "MONEY"]:
                results.append({
                    "type": ent.label_,
                    "value": ent.text,
                    "start": ent.start_char,
                    "end": ent.end_char
                })
        return results
