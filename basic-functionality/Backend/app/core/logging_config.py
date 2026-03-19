import logging
import logging.config
import sys
import warnings
from typing import Any, Dict

# Color codes for console output
class LogColors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"

class ColoredFormatter(logging.Formatter):
    """Custom formatter for rich, color-coded console output."""
    
    FORMATS = {
        logging.DEBUG: LogColors.CYAN + "%(levelname)s" + LogColors.RESET + ":     %(message)s",
        logging.INFO: LogColors.GREEN + "%(levelname)s" + LogColors.RESET + ":      %(message)s",
        logging.WARNING: LogColors.YELLOW + "%(levelname)s" + LogColors.RESET + ":   %(message)s",
        logging.ERROR: LogColors.RED + "%(levelname)s" + LogColors.RESET + ":     %(message)s",
        logging.CRITICAL: LogColors.BOLD + LogColors.RED + "%(levelname)s" + LogColors.RESET + ":  %(message)s",
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

def setup_logging():
    """Sets up the global logging configuration."""
    
    config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            },
            "colored": {
                "()": ColoredFormatter,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "colored",
                "stream": sys.stdout,
            },
            "file": {
                "class": "logging.FileHandler",
                "formatter": "standard",
                "filename": "reflect_backend.log",
                "mode": "a",
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "": {  # root logger
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": True,
            },
            "app": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }
    
    logging.config.dictConfig(config)
    
    # Suppress noisy library loggers
    for logger_name in [
        "transformers", 
        "sentence_transformers", 
        "whisperx", 
        "speechbrain", 
        "lightning", 
        "pytorch_lightning", 
        "thinc",
        "torch"
    ]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    # Filter specific persistent warnings
    warnings.filterwarnings("ignore", category=FutureWarning, module="thinc")
    warnings.filterwarnings("ignore", category=FutureWarning, module="torch")
    warnings.filterwarnings("ignore", message=".*Lightning automatically upgraded your loaded checkpoint.*")

setup_logging()
logger = logging.getLogger("app")
