import logging
import logging.config
import warnings
import sys
import os

# ============================================================
# LEVEL CONTROL
# Set LOG_LEVEL=DEBUG|INFO|WARNING|ERROR in the environment to
# change verbosity at startup without touching code.
# Default is DEBUG so nothing is hidden during development.
# ============================================================

_RAW_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()
_LEVEL = getattr(logging, _RAW_LEVEL, logging.DEBUG)

# ============================================================
# LOG FILE SETUP
# ============================================================

LOGS_DIR = "logs"
LOG_FILE = os.path.join(LOGS_DIR, "app.log")

os.makedirs(LOGS_DIR, exist_ok=True)


# ============================================================
# MAIN LOGGING SETUP FUNCTION
# ============================================================

def setup_logging():
    """
    Configures logging for the entire backend.

    Set LOG_LEVEL=INFO (or WARNING/ERROR) in the environment to
    reduce verbosity. Defaults to DEBUG so all detail is visible.
    """
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,

        "formatters": {
            "console": {
                "format": "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
                "datefmt": "%H:%M:%S",
            },
            "file": {
                "format": "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },

        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": _RAW_LEVEL,
                "formatter": "console",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.FileHandler",
                "level": "DEBUG",          # file always captures everything
                "formatter": "file",
                "filename": LOG_FILE,
                "encoding": "utf-8",
            },
        },

        "root": {
            "level": "DEBUG",              # root accepts all; handlers filter
            "handlers": ["console", "file"],
        },
    })

    # Silence noisy third-party libraries regardless of LOG_LEVEL.
    for noisy in (
        "httpx",
        "httpcore",
        "transformers",
        "torch",
        "sentence_transformers",
        "chromadb",
        "watchdog",
        "multipart",            # per-chunk debug spam during file uploads
        "fsevents",             # raw macOS kernel filesystem events from watchdog
        "matplotlib",           # font/cache/platform debug on every transcription load
        "torio",                # FFmpeg extension probe failures (harmless — we use subprocess ffmpeg)
        "fsspec",               # local file-open traces from pyannote VAD model loading
        "urllib3",              # HTTPS connection traces (HuggingFace, otel telemetry pings)
        "lightning",            # Lightning checkpoint upgrade notices
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    warnings.filterwarnings("ignore", message=".*resume_download.*")
    warnings.filterwarnings("ignore", message=".*use_auth_token.*")
    # torio/torchcodec probe every FFmpeg version on import and emit a UserWarning when
    # none of the .dylib files load. The warning is harmless — transcription uses the
    # system ffmpeg subprocess, not Python FFmpeg bindings.
    warnings.filterwarnings("ignore", message=".*torchcodec.*")
    warnings.filterwarnings("ignore", message=".*libtorchcodec.*")
    warnings.filterwarnings("ignore", message=".*FFmpeg.*extension.*")
    # pyannote wraps the torchcodec failure in its own UserWarning.
    warnings.filterwarnings("ignore", message=".*torchcodec is not installed correctly.*")

    logging.getLogger("reflect").info(
        "Logging initialised — console level=%s, file=DEBUG, log_file=%s",
        _RAW_LEVEL, LOG_FILE,
    )


# ============================================================
# INITIALIZE LOGGING IMMEDIATELY ON IMPORT
# ============================================================

setup_logging()

# ============================================================
# APPLICATION LOGGER
# ============================================================
# Import and use this everywhere:
#   from app.logging_config import logger
# ============================================================

logger = logging.getLogger("reflect")
