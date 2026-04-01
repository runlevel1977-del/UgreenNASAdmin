import json
import os
from pathlib import Path


APP_DATA_DIR = Path(os.environ.get("APP_DATA_DIR", "/app_data"))
CONFIG_DIR = APP_DATA_DIR / "config"
REPORTS_DIR = APP_DATA_DIR / "reports"
LOGS_DIR = APP_DATA_DIR / "logs"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
AUTH_FILE = CONFIG_DIR / "auth.json"


def ensure_dirs():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload):
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def get_settings():
    ensure_dirs()
    base = {
        "host": "",
        "port": 22,
        "user": "",
        "password": "",
        "ssh_use_key": False,
        "ssh_key_path": "",
        "ssh_key_passphrase": "",
    }
    base.update(read_json(SETTINGS_FILE, {}))
    try:
        base["port"] = int(base.get("port", 22))
    except Exception:
        base["port"] = 22
    return base


def save_settings(data: dict):
    ensure_dirs()
    curr = get_settings()
    curr.update(data)
    write_json(SETTINGS_FILE, curr)
    return curr
