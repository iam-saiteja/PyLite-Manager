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


def _looks_like_venv(directory: Path) -> tuple[bool, Path | None]:
    try:
        config_path = directory / "pyvenv.cfg"
        if config_path.is_file():
            return True, config_path

        scripts_python = directory / "Scripts" / "python.exe"
        scripts_activate = directory / "Scripts" / "activate.bat"
        scripts_pip = directory / "Scripts" / "pip.exe"
        lib_site_packages = directory / "Lib" / "site-packages"
        if scripts_python.is_file() and (scripts_activate.is_file() or scripts_pip.is_file() or lib_site_packages.is_dir()):
            return True, config_path if config_path.exists() else None

        scripts_dir = directory / "Scripts"
        if scripts_dir.is_dir() and lib_site_packages.is_dir():
            return True, config_path if config_path.exists() else None

        bin_python = directory / "bin" / "python"
        bin_activate = directory / "bin" / "activate"
        bin_pip = directory / "bin" / "pip"
        unix_site_packages = directory / "lib"
        if bin_python.is_file() and (bin_activate.is_file() or bin_pip.is_file() or unix_site_packages.is_dir()):
            return True, config_path if config_path.exists() else None

        bin_dir = directory / "bin"
        if bin_dir.is_dir() and unix_site_packages.is_dir():
            return True, config_path if config_path.exists() else None
    except PermissionError:
        pass

    return False, None


def find_venvs(scan_roots: Iterable[Path]) -> list[VenvInfo]:
    discovered: dict[str, VenvInfo] = {}
    ignored_names = {
        ".git",
        ".hg",
        ".svn",
        "__pycache__",
        "node_modules",
        ".mypy_cache",
        ".pytest_cache",
        ".tox",
        ".nox",
    }

    for root in scan_roots:
        if not root.exists():
            continue

        stack = [root]
        while stack:
            current_dir = stack.pop()

            is_current_venv, current_cfg = _looks_like_venv(current_dir)
            if is_current_venv:
                resolved_current = str(current_dir.resolve())
                if resolved_current not in discovered:
                    discovered[resolved_current] = VenvInfo(
                        name=current_dir.name,
                        path=current_dir,
                        python_version=_parse_pyvenv_cfg(current_cfg) if current_cfg is not None else "Unknown",
                        config_path=current_cfg if current_cfg is not None else current_dir / "pyvenv.cfg",
                    )
                continue

            try:
                with os.scandir(current_dir) as entries:
                    child_dirs: list[Path] = []
                    for entry in entries:
                        try:
                            if not entry.is_dir(follow_symlinks=False):
                                continue
                            child_path = Path(entry.path)
                            if child_path.name.lower() in ignored_names:
                                continue
                            child_dirs.append(child_path)
                            is_venv, config_path = _looks_like_venv(child_path)
                            if is_venv:
                                resolved = str(child_path.resolve())
                                if resolved not in discovered:
                                    discovered[resolved] = VenvInfo(
                                        name=child_path.name,
                                        path=child_path,
                                        python_version=_parse_pyvenv_cfg(config_path) if config_path is not None else "Unknown",
                                        config_path=config_path if config_path is not None else child_path / "pyvenv.cfg",
                                    )
                                continue
                        except OSError:
                            continue
                    stack.extend(child_dirs)
            except OSError:
                continue

    return sorted(discovered.values(), key=lambda item: (item.name.lower(), str(item.path).lower()))


import sys

def open_venv_terminal(venv_path: Path) -> None:
    if sys.platform == "win32":
        activate_path = venv_path / "Scripts" / "activate.bat"
        scripts_path = venv_path / "Scripts"
        root_python = venv_path / "python.exe"
        scripts_python = scripts_path / "python.exe"
        if activate_path.exists():
            command = f'cd /d "{venv_path}" && call "{activate_path}"'
        elif scripts_python.exists():
            command = (
                f'cd /d "{venv_path}" && '
                f'set "VIRTUAL_ENV={venv_path}" && '
                f'set "PATH={scripts_path};%PATH%"'
            )
        elif root_python.exists():
            command = f'cd /d "{venv_path}" && set "PATH={venv_path};%PATH%"'
        else:
            command = f'cd /d "{venv_path}"'
        subprocess.Popen(["cmd.exe", "/k", command])
    else:
        import tempfile
        import shlex

        activate_path = venv_path / "bin" / "activate"
        bin_path = venv_path / "bin"

        # Safely quote the venv path to prevent command injection
        safe_venv_path = shlex.quote(str(venv_path))
        safe_activate_path = shlex.quote(str(activate_path))
        safe_bin_path = shlex.quote(str(bin_path))

        if activate_path.exists():
            command = f'cd {safe_venv_path} && source {safe_activate_path} && exec $SHELL'
        elif (bin_path / "python").exists():
            command = f'cd {safe_venv_path} && export VIRTUAL_ENV={safe_venv_path} && export PATH="{safe_bin_path}:$PATH" && exec $SHELL'
        else:
            command = f'cd {safe_venv_path} && exec $SHELL'

        if sys.platform == "darwin":
            # On macOS, use open with Terminal or iTerm depending on what's available,
            # but simplest is generating a temp script and executing it with Terminal
            script = f'#!/bin/bash\n{command}\n'
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sh') as f:
                f.write(script)
                temp_sh_path = f.name

            Path(temp_sh_path).chmod(0o755)
            subprocess.Popen(["open", "-a", "Terminal", temp_sh_path])
        else:
            # On Linux, try x-terminal-emulator, gnome-terminal, etc.
            terminals = ["x-terminal-emulator", "gnome-terminal", "konsole", "xfce4-terminal", "xterm"]
            for term in terminals:
                if shutil.which(term):
                    if term == "gnome-terminal":
                        subprocess.Popen([term, "--", "bash", "-c", command])
                    else:
                        subprocess.Popen([term, "-e", "bash", "-c", command])
                    break


def open_folder(venv_path: Path) -> None:
    if sys.platform == "win32":
        subprocess.Popen(["explorer", str(venv_path)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(venv_path)])
    else:
        subprocess.Popen(["xdg-open", str(venv_path)])


def find_python_uninstaller(executable: Path) -> Path | None:
    install_root = executable.parent
    search_roots = [install_root]
    if install_root.parent != install_root:
        search_roots.append(install_root.parent)

    candidates: list[Path] = []
    for search_root in search_roots:
        if not search_root.exists():
            continue
        for pattern in ("uninstall*.exe", "*uninstall*.exe", "Uninstall*.exe"):
            candidates.extend(candidate for candidate in search_root.glob(pattern) if candidate.is_file())

    if not candidates:
        return None

    candidates.sort(key=lambda candidate: ("python" not in candidate.name.lower(), len(candidate.name), candidate.name.lower()))
    return candidates[0]


def uninstall_python_installation(executable: Path) -> Path:
    uninstaller = find_python_uninstaller(executable)
    if uninstaller is None:
        raise FileNotFoundError(f"No Python uninstaller was found near: {executable.parent}")

    subprocess.Popen([str(uninstaller)], cwd=str(uninstaller.parent))
    return uninstaller


def delete_venv(venv_path: Path) -> None:
    shutil.rmtree(venv_path)


def create_venv(target_path: Path, python_spec: str | None = None) -> str:
    command = ["py"]
    if python_spec:
        command.append(python_spec)
    command.extend(["-m", "venv", str(target_path)])
    result = run_command(command)
    return result.combined_output
