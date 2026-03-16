import logging
import logging.config
import warnings
import sys
import os

LOGS_DIR = "logs"
LOG_FILE = os.path.join(LOGS_DIR, "app.log")

os.makedirs(LOGS_DIR, exist_ok=True)


class ColoredFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG:    "\033[36m",   # cyan
        logging.INFO:     "\033[32m",   # green
        logging.WARNING:  "\033[33m",   # yellow
        logging.ERROR:    "\033[31m",   # red
        logging.CRITICAL: "\033[35m",   # magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        level = f"{color}{record.levelname:<8}{self.RESET}"
        return f"{level} {record.getMessage()}"


def setup_logging():
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(ColoredFormatter())

    file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "loggers": {
            "":                  {"level": "INFO", "propagate": False},
            "reflect":           {"level": "INFO", "propagate": False},
            "uvicorn":           {"level": "INFO", "propagate": False},
            "uvicorn.access":    {"level": "INFO", "propagate": False},
        },
    })

    for name in ("", "reflect"):
        lgr = logging.getLogger(name)
        lgr.handlers.clear()
        lgr.addHandler(console_handler)
        lgr.addHandler(file_handler)

    logging.getLogger("uvicorn").handlers.clear()
    logging.getLogger("uvicorn").addHandler(console_handler)
    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.access").addHandler(console_handler)

    # Silence noisy libraries
    for noisy in ("httpx", "httpcore", "transformers", "torch", "sentence_transformers"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    warnings.filterwarnings("ignore", message=".*resume_download.*")
    warnings.filterwarnings("ignore", message=".*use_auth_token.*")


# Runs at import time — logging is active before anything else loads
setup_logging()

logger = logging.getLogger("reflect")