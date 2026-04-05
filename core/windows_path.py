from __future__ import annotations

from pathlib import Path
import ctypes
import os
import winreg


def _normalize_entry(value: str) -> str:
    return str(Path(value)).rstrip("\\/").lower()


def _split_path_entries(raw_value: str) -> list[str]:
    return [part.strip() for part in raw_value.split(os.pathsep) if part.strip()]


def _join_path_entries(entries: list[str]) -> str:
    return os.pathsep.join(entries)


def get_user_path_entries() -> list[str]:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ) as key:
            value, _value_type = winreg.QueryValueEx(key, "Path")
            return _split_path_entries(value)
    except FileNotFoundError:
        return []
    except OSError:
        return []


def set_user_path_entries(entries: list[str]) -> None:
    normalized_entries: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        cleaned = str(Path(entry)).strip()
        if not cleaned:
            continue
        key = _normalize_entry(cleaned)
        if key in seen:
            continue
        seen.add(key)
        normalized_entries.append(cleaned)

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
        winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, _join_path_entries(normalized_entries))

    _broadcast_environment_change()


def prioritize_python_on_user_path(python_executable: str | Path) -> list[str]:
    executable_path = Path(python_executable)
    python_dir = executable_path.parent
    scripts_dir = python_dir / "Scripts"

    current_entries = get_user_path_entries()
    prioritized = [str(python_dir), str(scripts_dir)]

    remaining: list[str] = []
    seen: set[str] = set()
    for entry in prioritized + current_entries:
        key = _normalize_entry(entry)
        if key in seen:
            continue
        seen.add(key)
        remaining.append(str(Path(entry)))

    set_user_path_entries(remaining)
    return remaining


def _broadcast_environment_change() -> None:
    hwnd_broadcast = 0xFFFF
    wm_settingchange = 0x001A
    send_message_timeout = ctypes.windll.user32.SendMessageTimeoutW
    send_message_timeout.restype = ctypes.c_ulong
    send_message_timeout.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(ctypes.c_ulong)]
    result = ctypes.c_ulong()
    send_message_timeout(hwnd_broadcast, wm_settingchange, 0, "Environment", 0x0002, 5000, ctypes.byref(result))
