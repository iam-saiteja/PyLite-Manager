from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from utils.helpers import run_command


@dataclass(slots=True)
class PythonVersionInfo:
    spec: str
    display: str
    executable: str
    is_default: bool = False


def detect_python_versions() -> List[PythonVersionInfo]:
    result = run_command(["py", "-0p"])
    output = result.stdout.strip() or result.stderr.strip()
    versions: list[PythonVersionInfo] = []

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or line.lower().startswith("installed pythons"):
            continue

        is_default = "*" in line
        cleaned = line.replace("*", "").strip()
        if not cleaned.startswith("-"):
            continue

        parts = cleaned.split(maxsplit=1)
        spec = parts[0]
        executable = parts[1].strip() if len(parts) > 1 else ""
        display = _detect_full_version(executable) if executable else spec.lstrip("-")
        versions.append(PythonVersionInfo(spec=spec, display=display, executable=executable, is_default=is_default))

    return versions


def _detect_full_version(executable: str) -> str:
    result = run_command([
        executable,
        "-c",
        "import sys; print(sys.version.split()[0])",
    ])
    version = result.stdout.strip() or result.stderr.strip()
    if version:
        return version
    return Path(executable).stem
