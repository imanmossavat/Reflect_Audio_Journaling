import logging
import logging.config
import re
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
# POLLING NOISE FILTER
# The frontend runs several always-on background poll loops — GET /chats every
# 5s, GET /sources every 5s, GET /source/{id} every 2.5s while a source is
# processing — and each open tab runs all of them independently (see
# docs/ISSUES.md #21). With more than one tab open this floods the console
# with access-log lines that carry no debugging signal, drowning out the
# handful of lines that do. Only successful (2xx) polls are dropped — a
# failing poll is itself useful information and still logs normally.
# ============================================================

_POLLING_PATHS = re.compile(r"^/(chats|sources|source/\d+)$")


class _PollingAccessNoiseFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # uvicorn's access logger formats records with args
        # (client_addr, method, full_path, http_version, status_code).
        args = record.args
        if not isinstance(args, tuple) or len(args) < 5:
            return True
        method, full_path, status_code = args[1], args[2], args[4]
        if method != "GET" or not str(status_code).startswith("2"):
            return True
        path = str(full_path).split("?", 1)[0]
        return _POLLING_PATHS.match(path) is None


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
        "numba",                # JIT compilation traces from librosa (one-time, verbose)
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # Filters attach to the logger object itself, not to whichever handler is
    # currently wired to it — safe regardless of whether this runs before or
    # after uvicorn's own configure_logging() call reconfigures
    # "uvicorn.access"'s handlers (dictConfig never clears a logger's existing
    # filters unless the config explicitly lists a "filters" key for it, which
    # uvicorn's default LOGGING_CONFIG does not).
    logging.getLogger("uvicorn.access").addFilter(_PollingAccessNoiseFilter())

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
