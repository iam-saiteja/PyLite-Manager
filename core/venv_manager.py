from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import shutil
import subprocess
from typing import Iterable

from utils.helpers import run_command


@dataclass(slots=True)
class VenvInfo:
    name: str
    path: Path
    python_version: str
    config_path: Path


def _parse_pyvenv_cfg(config_path: Path) -> str:
    version = "Unknown"
    try:
        for raw_line in config_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" not in raw_line:
                continue
            key, value = raw_line.split("=", 1)
            if key.strip().lower() in {"version", "version_info"}:
                version = value.strip().split()[0]
                break
    except OSError:
        return "Unknown"
    return version or "Unknown"


def find_venvs(scan_roots: Iterable[Path]) -> list[VenvInfo]:
    discovered: dict[str, VenvInfo] = {}

    for root in scan_roots:
        if not root.exists():
            continue

        for dirpath, dirnames, filenames in os.walk(root):
            current_dir = Path(dirpath)
            if "pyvenv.cfg" in filenames:
                config_path = current_dir / "pyvenv.cfg"
                resolved = str(current_dir.resolve())
                if resolved not in discovered:
                    discovered[resolved] = VenvInfo(
                        name=current_dir.name,
                        path=current_dir,
                        python_version=_parse_pyvenv_cfg(config_path),
                        config_path=config_path,
                    )
                dirnames[:] = []

    return sorted(discovered.values(), key=lambda item: (item.name.lower(), str(item.path).lower()))


def open_venv_terminal(venv_path: Path) -> None:
    activate_path = venv_path / "Scripts" / "activate.bat"
    command = f'cd /d "{venv_path}" && call "{activate_path}"'
    subprocess.Popen(["cmd.exe", "/k", command])


def open_folder(venv_path: Path) -> None:
    subprocess.Popen(["explorer", str(venv_path)])


def delete_venv(venv_path: Path) -> None:
    shutil.rmtree(venv_path)


def create_venv(target_path: Path, python_spec: str | None = None) -> str:
    command = ["py"]
    if python_spec:
        command.append(python_spec)
    command.extend(["-m", "venv", str(target_path)])
    result = run_command(command)
    return result.combined_output
