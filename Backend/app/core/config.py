import json
import os
import threading
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # --- General --- #
    BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))

    # Default relative paths
    DATA_DIR: str = "data"
    CONFIG_DIR: str = "configs"
    LANGUAGE: str = "en"
    IS_CONFIGURED: bool = False

    # --- Transcription --- #
    WHISPER_MODEL: str = "base"
    DEVICE: str = "cpu"
    COMPUTE_TYPE: str = "float32"
    SAMPLE_RATE: int = 16000

    # --- Segmentation --- #
    SEGMENTATION_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    SEGMENTATION_STRATEGY: str = "adaptive"
    SEGMENTATION_SIMILARITY_METHOD: str = "percentile"
    SEGMENTATION_STD_FACTOR: float = 1.0
    SEGMENTATION_MIN_SIZE: int = 2
    SEGMENTATION_PERCENTILE: int = 20
    SEGMENTATION_TOPIC_TOP_N: int = 1

    # --- PII Detection --- #
    PII_REGEX_SENSITIVITY: str = "normal"
    PII_PATTERNS_PATH: str = "" # Set in __init__
    PII_PATTERNS: dict = Field(default_factory=dict)

    # --- Logging / Debug --- #
    LOG_LEVEL: str = "INFO"

    def load_overrides(self):
        forbidden_overrides = ["BASE_DIR", "CONFIG_DIR", "PII_PATTERNS_PATH"]
    
        current_script_path = os.path.abspath(__file__)
        self.BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(current_script_path), "../../"))
        self.CONFIG_DIR = os.path.join(self.BASE_DIR, "configs")
    
        frontend_path = os.path.join(self.CONFIG_DIR, "frontend_settings.json")
    
        if os.path.exists(frontend_path):
            try:
                with open(frontend_path, "r", encoding="utf-8") as f:
                    user_settings = json.load(f)
    
                for key, value in user_settings.items():
                    if key in forbidden_overrides:
                        continue
    
                    if hasattr(self, key):
                        setattr(self, key, value)
    
                self.IS_CONFIGURED = True
                print(f"Successfully loaded overrides from: {frontend_path}")
            except Exception as e:
                print(f"Error loading overrides: {e}")
                self.IS_CONFIGURED = False
        else:
            self.IS_CONFIGURED = False
    
        if not os.path.isabs(self.DATA_DIR):
            self.DATA_DIR = os.path.normpath(os.path.join(self.BASE_DIR, self.DATA_DIR))
        else:
            folder_name = os.path.basename(self.DATA_DIR)
            self.DATA_DIR = os.path.join(self.BASE_DIR, folder_name)
    
        os.makedirs(self.DATA_DIR, exist_ok=True)
        os.makedirs(self.CONFIG_DIR, exist_ok=True)
        
    def load_pii_patterns(self):
        if os.path.exists(self.PII_PATTERNS_PATH):
            try:
                with open(self.PII_PATTERNS_PATH, "r", encoding="utf-8") as f:
                    self.PII_PATTERNS = json.load(f)
                print(f"Loaded PII patterns: {len(self.PII_PATTERNS)} keys")
            except Exception as e:
                print(f"Could not load PII patterns: {e}")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.load_overrides()
        self.load_pii_patterns()

settings = Settings()