import time
import shutil
import httpx
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

INBOX = Path(__file__).parent.parent.parent / "database" / "inbox"
DONE = INBOX / "done"
SUPPORTED_EXT = {".wav", ".mp3", ".m4a", ".webm", ".ogg", ".txt", ".md"}


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


class InboxHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() not in SUPPORTED_EXT:
            return
        _wait_stable(path)
        if not path.exists():
            return
        try:
            with path.open("rb") as f:
                resp = httpx.post(
                    "http://localhost:8000/source/uploadFile/processed",
                    files={"file": (path.name, f, "application/octet-stream")},
                    timeout=600,
                )
            resp.raise_for_status()
            DONE.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), DONE / path.name)
            print(f"[inbox] processed and moved: {path.name}")
        except Exception as e:
            print(f"[inbox] failed to process {path.name}: {e}")


def start_watcher() -> Observer:
    INBOX.mkdir(parents=True, exist_ok=True)
    observer = Observer()
    observer.schedule(InboxHandler(), str(INBOX), recursive=False)
    observer.start()
    print(f"[inbox] watching {INBOX}")
    return observer
