import logging
import logging.config
import warnings
import sys
import os

# ============================================================
# LOG FILE SETUP
# ============================================================

LOGS_DIR = "logs"
LOG_FILE = os.path.join(LOGS_DIR, "app.log")

os.makedirs(LOGS_DIR, exist_ok=True)


# ============================================================
# OPTIONAL: COLORED CONSOLE OUTPUT
# ============================================================

class ColoredFormatter(logging.Formatter):
    """
    Adds ANSI colors to log level names for terminal readability.
    Only affects console output, NOT file logs.
    """

    COLORS = {
        logging.DEBUG: "\033[36m",    # cyan
        logging.INFO: "\033[32m",     # green
        logging.WARNING: "\033[33m",  # yellow
        logging.ERROR: "\033[31m",    # red
        logging.CRITICAL: "\033[35m", # magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        level = f"{color}{record.levelname:<8}{self.RESET}"
        return f"{level} {record.getMessage()}"


# ============================================================
# MAIN LOGGING SETUP FUNCTION
# ============================================================

def setup_logging():
    """
    Configures logging for the entire backend.

    Key design decisions:
    - ONE logging system (dictConfig only)
    - DEBUG enabled for full visibility
    - console + file output
    - no manual handler mutation
    """

    # --------------------------------------------------------
    # Console handler (colored output)
    # --------------------------------------------------------
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(ColoredFormatter())

    # --------------------------------------------------------
    # File handler (persistent logs)
    # --------------------------------------------------------
    file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    # --------------------------------------------------------
    # GLOBAL LOGGING CONFIG (IMPORTANT PART)
    # --------------------------------------------------------
    logging.config.dictConfig({
        "version": 1,

        # Do NOT override already-created loggers (uvicorn, fastapi, etc.)
        "disable_existing_loggers": False,

        # -----------------------
        # FORMATTERS
        # -----------------------
        "formatters": {
            "default": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            }
        },

        # -----------------------
        # HANDLERS
        # -----------------------
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.FileHandler",
                "level": "DEBUG",
                "formatter": "default",
                "filename": LOG_FILE,
                "encoding": "utf-8",
            },
        },

        # -----------------------
        # ROOT LOGGER (MOST IMPORTANT FIX)
        # -----------------------
        # This ensures ALL logs (including logger.info/debug) are visible.
        "root": {
            "level": "DEBUG",
            "handlers": ["console", "file"]
        },
    })

    # ========================================================
    # SILENCE NOISY THIRD-PARTY LIBRARIES
    # ========================================================
    for noisy in (
        "httpx",
        "httpcore",
        "transformers",
        "torch",
        "sentence_transformers"
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # ========================================================
    # PYTHON WARNING FILTERS (reduce spam)
    # ========================================================
    warnings.filterwarnings("ignore", message=".*resume_download.*")
    warnings.filterwarnings("ignore", message=".*use_auth_token.*")


# ============================================================
# INITIALIZE LOGGING IMMEDIATELY ON IMPORT
# ============================================================

setup_logging()

# ============================================================
# APPLICATION LOGGER
# ============================================================
# This is the logger you should import everywhere:
# from app.logging_config import logger
# ============================================================

logger = logging.getLogger("reflect")