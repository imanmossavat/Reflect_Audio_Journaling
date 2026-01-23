import os
import json
import tempfile
import threading
import logging
import platform
import subprocess
from app.core.config import settings

logger = logging.getLogger(__name__)

class SettingsManager:
    def __init__(self):
        self.frontend_path = os.path.join(settings.CONFIG_DIR, "frontend_settings.json")

    def get_effective_settings(self):
        """Merge backend defaults with user overrides."""
        user_settings = {}
        if os.path.exists(self.frontend_path):
            try:
                with open(self.frontend_path, "r", encoding="utf-8") as f:
                    user_settings = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load user settings: {e}")
        
        return {**settings.__dict__, **user_settings}

    def update_settings(self, payload: dict):
        """Save overrides and potentially trigger a restart."""
        should_restart = payload.pop("RESTART_REQUIRED", False)
        
        try:
            os.makedirs(settings.CONFIG_DIR, exist_ok=True)
            fd, temp_path = tempfile.mkstemp(dir=settings.CONFIG_DIR, text=True)
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)

            if os.path.exists(self.frontend_path):
                os.remove(self.frontend_path)
            os.rename(temp_path, self.frontend_path)
            
            # Refresh settings object in memory if possible (depends on implementation of settings.load_overrides)
            if hasattr(settings, "load_overrides"):
                settings.load_overrides()

            if should_restart:
                self._trigger_restart()

            return {"status": "ok", "restarting": should_restart}
        except Exception as e:
            logger.error(f"Failed to update settings: {e}")
            return {"status": "error", "message": str(e)}

    def reset_settings(self):
        """Delete user overrides."""
        if os.path.exists(self.frontend_path):
            os.remove(self.frontend_path)
            return True
        return False

    def open_folder(self, path: str):
        """Platform-specific folder opening."""
        if not path or not os.path.exists(path):
            return False, "Path not found"
        
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin": # macOS
                subprocess.Popen(["open", path])
            else: # Linux
                subprocess.Popen(["xdg-open", path])
            return True, None
        except Exception as e:
            return False, str(e)

    def _trigger_restart(self):
        def delayed_exit():
            import time
            time.sleep(0.8)
            os._exit(0)
        threading.Thread(target=delayed_exit, daemon=True).start()
