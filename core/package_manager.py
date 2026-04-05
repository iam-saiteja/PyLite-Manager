from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import textwrap
from utils.helpers import run_command


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
                rows.append(PackageInfo(name=parts[0], version=parts[1], latest=parts[2] if include_latest and len(parts) > 2 else ""))
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


def _package_scan_script() -> str:
    return textwrap.dedent(
        """
        import importlib.metadata as metadata
        import json

        def package_size(distribution):
            total = 0
            files = distribution.files or []
            for file_path in files:
                try:
                    resolved = distribution.locate_file(file_path)
                    if resolved.is_file():
                        total += resolved.stat().st_size
                except OSError:
                    continue
            return total

        rows = []
        for distribution in metadata.distributions():
            name = distribution.metadata.get('Name') or distribution.metadata.get('name') or ''
            if not name:
                continue
            rows.append({
                'name': name,
                'version': distribution.version or '',
                'size_bytes': package_size(distribution),
            })

        print(json.dumps(rows))
        """
    )


def list_packages(python_executable: Path | str) -> list[PackageInfo]:
    python_exe = _normalize_python_executable(python_executable)
    result = run_command([str(python_exe), "-c", _package_scan_script()])
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
                size_bytes=int(item.get("size_bytes", 0) or 0),
            )
        )
    return sorted(rows, key=lambda item: item.name.lower())


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
    return result.combined_output
