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
# Use the same filenames that start.sh generates with mkcert.
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
            logger.debug(f"[inbox] skipping {path.name} — already in-flight")
            return
        _inflight.add(key)
    try:
        if path.suffix.lower() not in SUPPORTED_EXT:
            logger.debug(f"[inbox] ignoring {path.name} — unsupported extension")
            return
        logger.info(f"[inbox] detected {path.name} — waiting for file to stabilise")
        _wait_stable(path)
        if not path.exists():
            # Recoverable: the capture was removed/moved before we got to it.
            logger.warning(f"[inbox] {path.name} disappeared before upload — skipping")
            return
        logger.info(f"[inbox] uploading {path.name} → {_UPLOAD_URL} (TLS={_USE_TLS})")
        try:
            with path.open("rb") as f:
                resp = httpx.post(
                    _UPLOAD_URL,
                    files={"file": (path.name, f, "application/octet-stream")},
                    timeout=600,
                    verify=False,
                )
            logger.debug(f"[inbox] upload response status={resp.status_code} for {path.name}")
            resp.raise_for_status()
            DONE.mkdir(parents=True, exist_ok=True)
            # Inbox names are no longer globally unique (no timestamp prefix), so a
            # same-named capture from an earlier session may already sit in done/.
            dest = unique_path(DONE, path.name)
            shutil.move(str(path), str(dest))
            logger.info(f"[inbox] {path.name} processed and moved to done/")
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
