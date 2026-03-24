import json
import sys
from pathlib import Path


def get_base_dir() -> Path:
    """Get the real app directory whether running frozen (PyInstaller) or as a script."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent.parent


APP_DIR = get_base_dir()
CONFIG_PATH = APP_DIR / "config.json"

DEFAULTS = {
    "model_id": "custom-voice-0.6b",
    "speaker": "Ryan",
    "language": "English",
    "instruct": "",
    "port": 7861,
    "auto_start_server": False,
    "show_setup_guide": True,
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            return {**DEFAULTS, **saved}
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULTS)


def save_config(config: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)