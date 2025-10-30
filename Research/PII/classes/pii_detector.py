import re
from structures.finding import PiiFinding
from patterns.default_patterns import DEFAULT_PATTERNS
from models.loader import load_model

class PIIDetector:
    """Detect and optionally redact Personally Identifiable Information (PII)."""
    def __init__(self, model, patterns=None):
        self.model_name = model
        self.nlp = load_model(model)
        self.patterns = patterns or DEFAULT_PATTERNS

    def detect(self, text, recording_id="test"):
        findings = []

        # regex pass
        for label, pattern in self.patterns.items():
            for m in re.finditer(pattern, text):
                findings.append(PiiFinding(recording_id, m.start(), m.end(), label, m.group(), "regex"))

        # model pass
        if hasattr(self.nlp, "pipe"):  # spaCy
            doc = self.nlp(text)
            for ent in getattr(doc, "ents", []):
                if ent.label_ in ["PERSON", "GPE", "ORG", "LOC", "DATE", "MONEY"]:
                    findings.append(PiiFinding(recording_id, ent.start_char, ent.end_char, ent.label_, ent.text, "ner"))

        elif callable(self.nlp):  # HuggingFace
            for e in self.nlp(text):
                findings.append(PiiFinding(recording_id, e["start"], e["end"], e["entity_group"], e["word"], "hf"))

        # deduplicate
        seen, unique = set(), []
        for f in findings:
            key = (f.start_char, f.end_char, f.label)
            if key not in seen:
                seen.add(key)
                unique.append(f)

        return unique

    def redact(self, text):
        findings = self.detect(text)
        for f in sorted(findings, key=lambda x: x.start_char, reverse=True):
            text = text[:f.start_char] + f"[REDACTED:{f.label}]" + text[f.end_char:]
        return text
