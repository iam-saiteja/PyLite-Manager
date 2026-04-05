from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import subprocess
import sys
import typing

from utils.helpers import run_command


def get_package_version(python_executable: Path | str, package_name: str) -> str:
    python_exe = _normalize_python_executable(python_executable)
    result = run_command([
        str(python_exe),
        "-m",
        "pip",
        "show",
        package_name,
        "--disable-pip-version-check",
    ])
    if result.returncode != 0:
        return ""

    for line in result.stdout.splitlines():
        if line.lower().startswith("version:"):
            return line.split(":", 1)[1].strip()
    return ""


@dataclass(slots=True)
class PackageInfo:
    name: str
    version: str
    size_bytes: int = 0
    latest: str = ""


def _normalize_python_executable(python_executable: Path | str) -> Path:
    return Path(python_executable)


def _read_package_rows(output: str, include_latest: bool = False) -> list[PackageInfo]:
    rows: list[PackageInfo] = []
    text = output.strip()
    if not text:
        return rows

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines[2:]:
            parts = line.split()
            if len(parts) >= 2:
                rows.append(
                    PackageInfo(
                        name=parts[0],
                        version=parts[1],
                        latest=parts[2] if include_latest and len(parts) > 2 else "",
                    )
                )
        return rows

    for item in payload:
        rows.append(
            PackageInfo(
                name=item.get("name", ""),
                version=item.get("version", ""),
                latest=item.get("latest_version", "") if include_latest else "",
            )
        )
    return rows


def list_packages(python_executable: Path | str) -> list[PackageInfo]:
    python_exe = _normalize_python_executable(python_executable)
    result = run_command(
        [
            str(python_exe),
            "-m",
            "pip",
            "list",
            "--format=json",
            "--disable-pip-version-check",
        ]
    )
    output = result.stdout.strip() or result.stderr.strip()
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return sorted(_read_package_rows(output), key=lambda item: item.name.lower())

    rows: list[PackageInfo] = []
    for item in payload:
        rows.append(
            PackageInfo(
                name=item.get("name", ""),
                version=item.get("version", ""),
            )
        )
    return sorted(rows, key=lambda item: item.name.lower())


def stream_package_sizes(python_executable: Path | str) -> typing.Iterator[tuple[str, int]]:
    """Yields (package_name, size_bytes) as they are calculated."""
    import subprocess
    import json
    python_exe = _normalize_python_executable(python_executable)
    process = subprocess.Popen(
        [
            str(python_exe),
            "-c",
            "import importlib.metadata as m, json, sys\n"
            "for d in m.distributions():\n"
            "    name = d.metadata.get('Name') or d.metadata.get('name') or ''\n"
            "    if not name: continue\n"
            "    total = 0\n"
            "    for file_path in d.files or []:\n"
            "        try:\n"
            "            resolved = d.locate_file(file_path)\n"
            "            if resolved.is_file(): total += resolved.stat().st_size\n"
            "        except OSError:\n"
            "            pass\n"
            "    sys.stdout.write(json.dumps({'name': name, 'size_bytes': total}) + '\\n')\n"
            "    sys.stdout.flush()\n"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    if process.stdout:
        for line in process.stdout:
            line = line.strip()
            if not line: continue
            try:
                data = json.loads(line)
                yield data.get('name', ''), int(data.get('size_bytes', 0) or 0)
            except json.JSONDecodeError:
                pass
    process.wait()

def load_package_sizes(python_executable: Path | str) -> list[PackageInfo]:
    python_exe = _normalize_python_executable(python_executable)
    result = run_command(
        [
            str(python_exe),
            "-c",
            "import importlib.metadata as m, json\n"
            "rows=[]\n"
            "for d in m.distributions():\n"
            "    name = d.metadata.get('Name') or d.metadata.get('name') or ''\n"
            "    if not name: continue\n"
            "    total = 0\n"
            "    for file_path in d.files or []:\n"
            "        try:\n"
            "            resolved = d.locate_file(file_path)\n"
            "            if resolved.is_file(): total += resolved.stat().st_size\n"
            "        except OSError:\n"
            "            pass\n"
            "    rows.append({'name': name, 'size_bytes': total})\n"
            "print(json.dumps(rows))\n",
        ]
    )
    output = result.stdout.strip() or result.stderr.strip()
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return []

    rows: list[PackageInfo] = []
    for item in payload:
        rows.append(
            PackageInfo(
                name=item.get("name", ""),
                version="",
                size_bytes=int(item.get("size_bytes", 0) or 0),
            )
        )
    return rows


def list_outdated_packages(python_executable: Path | str) -> list[PackageInfo]:
    python_exe = _normalize_python_executable(python_executable)
    result = run_command(
        [
            str(python_exe),
            "-m",
            "pip",
            "list",
            "--outdated",
            "--format=json",
            "--disable-pip-version-check",
        ]
    )
    output = result.stdout.strip() or result.stderr.strip()
    return sorted(_read_package_rows(output, include_latest=True), key=lambda item: item.name.lower())


def install_package(python_executable: Path | str, package_spec: str) -> str:
    python_exe = _normalize_python_executable(python_executable)
    result = run_command([
        str(python_exe),
        "-m",
        "pip",
        "install",
        package_spec,
        "--disable-pip-version-check",
    ])
    if result.returncode != 0:
        raise RuntimeError(result.combined_output or f"Failed to install {package_spec}")
    return result.combined_output


def uninstall_package(python_executable: Path | str, package_name: str) -> str:
    python_exe = _normalize_python_executable(python_executable)
    result = run_command([
        str(python_exe),
        "-m",
        "pip",
        "uninstall",
        "-y",
        package_name,
        "--disable-pip-version-check",
    ])
    if result.returncode != 0:
        raise RuntimeError(result.combined_output or f"Failed to uninstall {package_name}")
    return result.combined_output


def upgrade_package(python_executable: Path | str, package_name: str) -> str:
    python_exe = _normalize_python_executable(python_executable)
    result = run_command([
        str(python_exe),
        "-m",
        "pip",
        "install",
        "--upgrade",
        package_name,
        "--disable-pip-version-check",
    ])
    if result.returncode != 0:
        raise RuntimeError(result.combined_output or f"Failed to upgrade {package_name}")
    return result.combined_output
