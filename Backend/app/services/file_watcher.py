import threading
import time
import shutil
import httpx
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from app.logging_config import logger
from app.utils.unique_path import unique_path

INBOX = Path(__file__).parent.parent.parent / "database" / "inbox"
DONE = INBOX / "done"
SUPPORTED_EXT = {".wav", ".mp3", ".m4a", ".webm", ".ogg", ".txt", ".md"}

_CERT_DIR = Path(__file__).parent.parent.parent.parent / "certs"
_USE_TLS = (_CERT_DIR / "localhost.pem").exists() and (_CERT_DIR / "localhost-key.pem").exists()
_UPLOAD_URL = f"{'https' if _USE_TLS else 'http'}://localhost:8000/source/uploadFile/processed"

_inflight: set[str] = set()
_inflight_lock = threading.Lock()


def _wait_stable(path: Path, interval: float = 1.0, rounds: int = 3):
    prev = -1
    stable = 0
    while stable < rounds:
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            return
        if size == prev:
            stable += 1
        else:
            stable = 0
        prev = size
        time.sleep(interval)


def _process_file(path: Path):
    key = str(path.resolve())
    with _inflight_lock:
        if key in _inflight:
            return
        _inflight.add(key)
    try:
        if path.suffix.lower() not in SUPPORTED_EXT:
            return
        _wait_stable(path)
        if not path.exists():
            # Recoverable: the capture was removed/moved before we got to it.
            return
        try:
            with path.open("rb") as f:
                resp = httpx.post(
                    _UPLOAD_URL,
                    files={"file": (path.name, f, "application/octet-stream")},
                    timeout=600,
                    verify=False,
                )
            resp.raise_for_status()
            DONE.mkdir(parents=True, exist_ok=True)
            # Inbox names are no longer globally unique (no timestamp prefix), so a
            # same-named capture from an earlier session may already sit in done/.
            shutil.move(str(path), str(unique_path(DONE, path.name)))
        except Exception as e:
            logger.exception(f"[inbox] failed to process {path.name}: {e}")
    finally:
        with _inflight_lock:
            _inflight.discard(key)


class InboxHandler(FileSystemEventHandler):
    def _handle(self, src_path: str, event_label: str):
        path = Path(src_path)
        if path.suffix.lower() not in SUPPORTED_EXT:
            return
        # Only process files that sit directly in the inbox root. This prevents
        # reprocessing the file once it has been moved into done/ — the move
        # itself fires an on_moved event whose dest_path points into done/.
        if path.parent.resolve() != INBOX.resolve():
            return
        threading.Thread(target=_process_file, args=(path,), daemon=True).start()

    def on_created(self, event):
        if event.is_directory:
            return
        self._handle(event.src_path, "created")

    def on_moved(self, event):
        if event.is_directory:
            return
        self._handle(event.dest_path, "moved")

    def on_modified(self, event):
        # Some tools (cloud sync, editors) write via modify rather than create
        if event.is_directory:
            return
        self._handle(event.src_path, "modified")


def _sweep_existing():
    if not INBOX.exists():
        return
    for path in INBOX.iterdir():
        if path.is_dir():
            continue
        if path.suffix.lower() not in SUPPORTED_EXT:
            continue
        threading.Thread(target=_process_file, args=(path,), daemon=True).start()


def start_watcher():
    try:
        INBOX.mkdir(parents=True, exist_ok=True)
        observer = Observer()
        observer.schedule(InboxHandler(), str(INBOX), recursive=False)
        observer.start()
        _sweep_existing()
        return observer
    except Exception:
        logger.exception("[inbox] failed to start watcher")
        raise
