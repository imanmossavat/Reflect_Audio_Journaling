# app/core/config.py
import json
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # --- General ---
    BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))

    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    CONFIG_DIR: str = os.path.join(BASE_DIR, "configs")
    LANGUAGE: str = "en"

    # --- Transcription ---
    WHISPER_MODEL: str = "small"
    DEVICE: str = "cpu" # or "cuda"
    COMPUTE_TYPE: str = "float32"
    SAMPLE_RATE: int = 16000

    # --- Segmentation ---
    SEGMENTATION_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    SEGMENTATION_METHOD: str = "adaptive"  # or "spectral"
    SEGMENTATION_STD_FACTOR: float = 1.0
    SEGMENTATION_MIN_SIZE: int = 2
    SEGMENTATION_PERCENTILE: int = 20
    SEGMENTATION_TOPIC_TOP_N: int = 1

    # --- PII Detection ---
    PII_REGEX_SENSITIVITY: str = "normal"
    PII_PATTERNS_PATH: str = os.path.join(CONFIG_DIR, "pii_patterns.json")
    PII_PATTERNS: dict | None = None

    @property
    def pii_patterns(self):
        with open(self.PII_PATTERNS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # load once and store uppercase alias
        self.PII_PATTERNS = self.pii_patterns

    # --- Logging / Debug ---
    LOG_LEVEL: str = "INFO"

settings = Settings()
