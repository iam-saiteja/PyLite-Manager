from __future__ import annotations

from pathlib import Path
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from core.package_manager import list_packages
from core.python_detector import detect_python_versions
from core.venv_manager import delete_venv, find_venvs, open_venv_terminal
from core.windows_path import get_user_path_entries, prioritize_python_on_user_path
from ui.package_panel import PackagePanel
from ui.venv_panel import VenvPanel
from utils.config import load_config, save_config
from utils.helpers import calculate_directory_size, normalize_paths


class MainWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("PyLite Manager")
        self.geometry("1240x780")
        self.minsize(1080, 680)

        self.config_data = load_config()
        self.python_versions = []
        self.venvs = []
        self.selected_venv = None
        self.selected_python = None
        self.selected_python_source = ""
        self._package_load_token = 0

        self._busy_count = 0
        self._build_style()
        self._build_layout()
        self.after(100, self.refresh_all)

    def _build_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Section.TLabel", font=("Segoe UI", 10, "bold"))

    def _build_layout(self) -> None:
        root = ttk.Frame(self, padding=10)
        root.pack(fill=tk.BOTH, expand=True)

        paned = ttk.Panedwindow(root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(paned)
        right = ttk.Frame(paned)

        paned.add(left, weight=1)
        paned.add(right, weight=3)

        self.venv_panel = VenvPanel(left)
        self.venv_panel.pack(fill=tk.BOTH, expand=True)

        self.package_panel = PackagePanel(right)
        self.package_panel.pack(fill=tk.BOTH, expand=True)

        self.status_var = tk.StringVar(value="Ready")
        status = ttk.Label(root, textvariable=self.status_var, anchor=tk.W)
        status.pack(fill=tk.X, pady=(8, 0))

        self.venv_panel.set_actions(
            self.add_scan_folder,
            self.remove_scan_folder,
            self.open_selected_terminal,
            self.delete_selected_venv,
            self.apply_filter,
            self.set_default_python,
        )
        self.venv_panel.set_selection_callbacks(self.select_python_version, self.select_venv)

    def set_status(self, message: str) -> None:
        self.status_var.set(message)

    def run_async(self, worker, on_success=None, on_error=None) -> None:
        self._busy_count += 1
        self.set_status("Working...")

        def _task() -> None:
            try:
                result = worker()
            except Exception as exc:  # pragma: no cover - UI safety
                self.after(0, lambda: self._finish_async(None, exc, on_success, on_error))
            else:
                self.after(0, lambda: self._finish_async(result, None, on_success, on_error))

        threading.Thread(target=_task, daemon=True).start()

    def _finish_async(self, result, error, on_success, on_error) -> None:
        self._busy_count = max(0, self._busy_count - 1)
        if error is not None:
            self.set_status("Ready")
            if on_error is not None:
                on_error(error)
            else:
                messagebox.showerror("PyLite Manager", str(error), parent=self)
            return

        try:
            if on_success is not None:
                on_success(result)
        finally:
            self.set_status("Ready")

    def refresh_all(self) -> None:
        self.venv_panel.set_scan_folders(self.config_data.get("scan_folders", []))

        def worker():
            scan_roots = [Path(folder) for folder in self.config_data.get("scan_folders", [])]
            return detect_python_versions(), find_venvs(scan_roots)

        def success(result):
            python_versions, venvs = result
            python_versions = self._prioritize_python_by_path(python_versions)
            self.python_versions = python_versions
            self.venvs = venvs
            self.venv_panel.set_python_versions(python_versions)
            self.venv_panel.set_venvs(venvs)
            self.apply_filter()
            self.restore_default_selection()

        self.run_async(worker, success)

    def _prioritize_python_by_path(self, versions):
        if not versions:
            return versions

        path_entries = get_user_path_entries()
        normalized_path_entries = [str(Path(entry)).strip().lower() for entry in path_entries]
        prioritized = list(versions)

        def sort_key(version):
            python_dir = str(Path(version.executable).parent).strip().lower()
            scripts_dir = str(Path(version.executable).parent / "Scripts").strip().lower()
            try:
                python_score = normalized_path_entries.index(python_dir)
            except ValueError:
                python_score = len(normalized_path_entries)
            try:
                scripts_score = normalized_path_entries.index(scripts_dir)
            except ValueError:
                scripts_score = len(normalized_path_entries)
            return min(python_score, scripts_score)

        prioritized.sort(key=sort_key)

        selected_path = prioritized[0].executable if prioritized else ""
        for version in prioritized:
            python_dir = str(Path(version.executable).parent).strip().lower()
            scripts_dir = str(Path(version.executable).parent / "Scripts").strip().lower()
            python_score = normalized_path_entries.index(python_dir) if python_dir in normalized_path_entries else -1
            scripts_score = normalized_path_entries.index(scripts_dir) if scripts_dir in normalized_path_entries else -1
            version.path_rank = min([score for score in (python_score, scripts_score) if score >= 0], default=-1) + 1 if any(score >= 0 for score in (python_score, scripts_score)) else -1
            version.is_default = str(version.executable).strip().lower() == str(selected_path).strip().lower()

        return prioritized

    def restore_default_selection(self) -> None:
        if self.python_versions:
            self.select_python_version(self.python_versions[0])
            return
        if self.venvs:
            self.select_venv(self.venvs[0])

    def apply_filter(self) -> None:
        self.venv_panel.set_venvs(self.venvs)

    def add_scan_folder(self) -> None:
        folder = filedialog.askdirectory(title="Select folder to scan for virtual environments", parent=self)
        if not folder:
            return
        folders = normalize_paths(self.config_data.get("scan_folders", []) + [folder])
        self.config_data["scan_folders"] = folders
        save_config(self.config_data)
        self.venv_panel.set_scan_folders(folders)
        self.refresh_all()

    def remove_scan_folder(self) -> None:
        folder = self.venv_panel.get_scan_folder_selection()
        if not folder:
            return
        folders = [item for item in self.config_data.get("scan_folders", []) if Path(item) != Path(folder)]
        self.config_data["scan_folders"] = folders
        save_config(self.config_data)
        self.venv_panel.set_scan_folders(folders)
        self.refresh_all()

    def _require_selected_python(self):
        python_executable = self.package_panel.get_selected_python_executable()
        if python_executable is None:
            messagebox.showinfo("PyLite Manager", "Select a Python version or virtual environment first.", parent=self)
            return None
        return python_executable

    def _require_selected_venv(self):
        venv = self.venv_panel.get_selected_venv()
        if venv is None:
            messagebox.showinfo("PyLite Manager", "Select a virtual environment first.", parent=self)
            return None
        return venv

    def select_python_version(self, version) -> None:
        if version is None:
            return
        self.selected_python = version
        self.selected_python_source = "python"
        label = f"Global Python | {version.display} | {version.executable}"
        self.package_panel.set_selected_target(Path(version.executable), label)
        self.refresh_packages()

    def select_venv(self, venv) -> None:
        if venv is None:
            return
        self.selected_venv = venv
        self.selected_python = None
        self.selected_python_source = "venv"
        python_executable = venv.path / "Scripts" / "python.exe"
        label = f"Virtual Environment | {venv.name} | {venv.path} | Python {venv.python_version}"
        self.package_panel.set_selected_target(python_executable, label)
        self.refresh_packages()

    def set_default_python(self) -> None:
        version = self.venv_panel.get_selected_python_version()
        if version is None:
            messagebox.showinfo("PyLite Manager", "Select a Python version first.", parent=self)
            return
        try:
            prioritize_python_on_user_path(version.executable)
        except Exception as exc:  # pragma: no cover - environment safety
            messagebox.showerror("PyLite Manager", f"Unable to update PATH: {exc}", parent=self)
            return

        self.config_data["default_python_path"] = str(version.executable)
        save_config(self.config_data)
        self.python_versions = self._prioritize_python_by_path(self.python_versions)
        self.venv_panel.set_python_versions(self.python_versions)
        self.select_python_version(version)
        messagebox.showinfo(
            "PyLite Manager",
            f"Default Python updated to:\n{version.display}\n\nWindows PATH has been updated.",
            parent=self,
        )

    def refresh_packages(self) -> None:
        python_executable = self._require_selected_python()
        if python_executable is None:
            return

        self._package_load_token += 1
        token = self._package_load_token
        self.package_panel.set_loading("Loading packages...")

        def worker():
            target_root = python_executable.parent.parent if python_executable.parent.name.lower() == "scripts" else python_executable.parent
            total_size = calculate_directory_size(target_root)
            packages = list_packages(python_executable)
            return total_size, packages

        def success(result):
            total_size, packages = result
            if token != self._package_load_token:
                return
            self.package_panel.set_target_size(total_size)
            self.package_panel.show_packages_iteratively(packages)

        self.run_async(worker, success)

    def open_selected_terminal(self) -> None:
        venv = self._require_selected_venv()
        if venv is None:
            return
        try:
            open_venv_terminal(venv.path)
        except Exception as exc:  # pragma: no cover - UI safety
            messagebox.showerror("PyLite Manager", str(exc), parent=self)

    def delete_selected_venv(self) -> None:
        venv = self._require_selected_venv()
        if venv is None:
            return
        if not messagebox.askyesno("PyLite Manager", f"Delete virtual environment?\n\n{venv.path}", parent=self):
            return

        def worker():
            delete_venv(venv.path)
            return venv.path

        def success(_result):
            self.refresh_all()

        self.run_async(worker, success)
