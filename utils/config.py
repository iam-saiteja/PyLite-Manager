from __future__ import annotations

import json
from pathlib import Path
import os


APP_DIR_NAME = "PyLite_Manager"
CONFIG_FILE_NAME = "config.json"


def get_config_path() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        base_dir = Path(local_app_data)
    else:
        base_dir = Path.home() / "AppData" / "Local"
    return base_dir / APP_DIR_NAME / CONFIG_FILE_NAME


def load_config() -> dict:
    path = get_config_path()
    if not path.exists():
        return {"scan_folders": [], "default_python_path": ""}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"scan_folders": [], "default_python_path": ""}

    scan_folders = payload.get("scan_folders", [])
    if not isinstance(scan_folders, list):
        scan_folders = []

    default_python_path = payload.get("default_python_path", "")
    if not isinstance(default_python_path, str):
        default_python_path = ""

    return {
        "scan_folders": [str(Path(folder)) for folder in scan_folders if str(folder).strip()],
        "default_python_path": default_python_path.strip(),
    }


def save_config(config: dict) -> None:
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "scan_folders": [str(Path(folder)) for folder in config.get("scan_folders", [])],
        "default_python_path": str(config.get("default_python_path", "")).strip(),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
