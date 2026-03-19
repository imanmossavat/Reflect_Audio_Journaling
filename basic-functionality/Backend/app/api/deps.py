from functools import lru_cache
from fastapi import Depends
from app.services.storage import StorageManager
from app.services.storage.base import FileEngine
from app.services.storage.metadata import MetadataService
from app.services.storage.audio import AudioStorageService
from app.services.storage.transcripts import TranscriptService
from app.services.transcription import TranscriptionManager
from app.services.segmentation import SegmentationManager
from app.services.pii import PIIDetector
from app.services.prosody import ProsodyManager
from app.services.semantic_search import SemanticSearchManager
from app.services.settings import SettingsManager
from app.services.recordings import RecordingService
from app.core.logging_config import logger

# --- Dependency Injection Providers ---
# Using @lru_cache(None) ensures these managers behave as singletons.
# This prevents redundant loading of heavy AI models (WhisperX, spaCy).

@lru_cache(None)
def get_file_engine() -> FileEngine:
    return FileEngine()

@lru_cache(None)
def get_metadata_service(engine: FileEngine = Depends(get_file_engine)) -> MetadataService:
    return MetadataService(engine)

@lru_cache(None)
def get_audio_storage(
    engine: FileEngine = Depends(get_file_engine),
    metadata: MetadataService = Depends(get_metadata_service)
) -> AudioStorageService:
    return AudioStorageService(engine, metadata)

@lru_cache(None)
def get_transcript_storage(
    engine: FileEngine = Depends(get_file_engine),
    metadata: MetadataService = Depends(get_metadata_service)
) -> TranscriptService:
    return TranscriptService(engine, metadata)

@lru_cache(None)
def get_storage_manager(
    engine: FileEngine = Depends(get_file_engine),
    metadata: MetadataService = Depends(get_metadata_service),
    audio: AudioStorageService = Depends(get_audio_storage),
    transcripts: TranscriptService = Depends(get_transcript_storage)
) -> StorageManager:
    logger.info("Initializing StorageManager (Facade)...")
    return StorageManager(engine, metadata, audio, transcripts)

@lru_cache(None)
def get_transcription_manager() -> TranscriptionManager:
    logger.info("Initializing TranscriptionManager (WhisperX)...")
    return TranscriptionManager()

@lru_cache(None)
def get_segmentation_manager() -> SegmentationManager:
    logger.info("Initializing SegmentationManager (spaCy)...")
    return SegmentationManager()

@lru_cache(None)
def get_pii_detector() -> PIIDetector:
    logger.info("Initializing PIIDetector...")
    return PIIDetector()

@lru_cache(None)
def get_prosody_manager() -> ProsodyManager:
    logger.info("Initializing ProsodyManager...")
    return ProsodyManager()

@lru_cache(None)
def get_semantic_search_manager() -> SemanticSearchManager:
    logger.info("Initializing SemanticSearchManager...")
    return SemanticSearchManager()

@lru_cache(None)
def get_settings_manager() -> SettingsManager:
    logger.info("Initializing SettingsManager...")
    return SettingsManager()

def get_recording_service(
    storage: StorageManager = Depends(get_storage_manager)
) -> RecordingService:
    return RecordingService(storage)
