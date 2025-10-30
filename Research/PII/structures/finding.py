from dataclasses import dataclass

@dataclass
class PiiFinding:
    recording_id: str
    start_char: int
    end_char: int
    label: str
    preview: str
    source: str