from __future__ import annotations

from pathlib import Path
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from core.package_manager import (
    get_package_version,
    install_package as pkg_install,
    list_packages,
    stream_package_sizes,
    upgrade_package as pkg_upgrade,
    uninstall_package as pkg_uninstall,
    export_requirements as pkg_export,
    import_requirements as pkg_import,
    export_requirements as pkg_export,
    import_requirements as pkg_import,
)
from core.python_detector import detect_python_versions
from core.venv_manager import create_venv, delete_venv, find_venvs, open_folder, open_venv_terminal, uninstall_python_installation
from core.windows_path import get_user_path_entries, prioritize_python_on_user_path
from ui.package_panel import PackagePanel
from ui.venv_panel import VenvPanel
from utils.config import load_config, save_config
from utils.helpers import calculate_directory_size, format_bytes, normalize_paths


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
        self._pending_package_size_maps: dict[int, dict[str, int]] = {}

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

        # Modern color palette
        bg_color = "#f4f5f7"
        fg_color = "#333333"
        accent_color = "#0078D7"

        style.configure(".", background=bg_color, foreground=fg_color, font=("Segoe UI", 9))
        style.configure("TFrame", background=bg_color)
        style.configure("Section.TLabel", font=("Segoe UI", 11, "bold"), foreground=accent_color, background=bg_color)
        style.configure("TLabel", background=bg_color)
        style.configure("TButton", padding=6, relief="flat", background="#e1e1e1")
        style.map("TButton", background=[("active", "#d4d4d4"), ("disabled", "#f0f0f0")])
        style.configure("Treeview", background="#ffffff", fieldbackground="#ffffff", foreground=fg_color, rowheight=28, borderwidth=0)
        style.map("Treeview", background=[("selected", accent_color)], foreground=[("selected", "#ffffff")])
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), relief="flat", background="#e1e1e1", padding=4)

        # Modern color palette
        bg_color = "#f4f5f7"
        fg_color = "#333333"
        accent_color = "#0078D7"

        style.configure(".", background=bg_color, foreground=fg_color, font=("Segoe UI", 9))
        style.configure("TFrame", background=bg_color)
        style.configure("Section.TLabel", font=("Segoe UI", 11, "bold"), foreground=accent_color, background=bg_color)
        style.configure("TLabel", background=bg_color)
        style.configure("TButton", padding=6, relief="flat", background="#e1e1e1")
        style.map("TButton", background=[("active", "#d4d4d4"), ("disabled", "#f0f0f0")])
        style.configure("Treeview", background="#ffffff", fieldbackground="#ffffff", foreground=fg_color, rowheight=28, borderwidth=0)
        style.map("Treeview", background=[("selected", accent_color)], foreground=[("selected", "#ffffff")])
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), relief="flat", background="#e1e1e1", padding=4)

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
        self.package_panel.set_callbacks(
            on_refresh=self.refresh_packages,
            on_update=self.upgrade_package,
            on_degrade=self.degrade_package,
            on_delete=self.uninstall_package,
            on_export=self.export_requirements,
            on_import=self.import_requirements,
            on_stats=self.show_package_stats,
        )

        self.status_var = tk.StringVar(value="Ready")
        status = ttk.Label(root, textvariable=self.status_var, anchor=tk.W)
        status.pack(fill=tk.X, pady=(8, 0))

        self.status_progress = ttk.Progressbar(root, mode="indeterminate")
        self._status_progress_visible = False

        self.venv_panel.set_actions(
            self.add_scan_folder,
            self.remove_scan_folder,
            self.refresh_virtual_environments,
            self.search_virtual_environments,
            self.set_default_python,
            self.create_virtual_environment,
        )
        self.venv_panel.set_venv_context_actions(self.open_selected_folder)
        self.venv_panel.set_venv_delete_action(self.delete_selected_venv)
        self.venv_panel.set_venv_advanced_actions(self.backup_selected_venv, self.clone_selected_venv)
        self.venv_panel.set_python_context_actions(self.open_selected_python_folder)
        self.venv_panel.set_selection_callbacks(self.select_python_version, self.select_venv)

        self.after(0, lambda: paned.sashpos(0, 360))

    def set_status(self, message: str) -> None:
        self.status_var.set(message)

    def _begin_status_progress(self, message: str) -> None:
        self.set_status(message)
        if not self._status_progress_visible:
            self.status_progress.pack(fill=tk.X, pady=(4, 0))
            self._status_progress_visible = True
        self.status_progress.start(12)

    def _end_status_progress(self, message: str) -> None:
        self.status_progress.stop()
        if self._status_progress_visible:
            self.status_progress.pack_forget()
            self._status_progress_visible = False
        self.set_status(message)

    def run_async(self, worker, on_success=None, on_error=None, status_message: str = "Working...", completion_message: str | None = "Ready") -> None:
        self._busy_count += 1
        self.set_status(status_message)

        def _task() -> None:
            try:
                result = worker()
            except Exception as exc:  # pragma: no cover - UI safety
                self.after(0, self._finish_async, None, exc, on_success, on_error, completion_message)
            else:
                self.after(0, self._finish_async, result, None, on_success, on_error, completion_message)

        threading.Thread(target=_task, daemon=True).start()

    def _finish_async(self, result, error, on_success, on_error, completion_message) -> None:
        self._busy_count = max(0, self._busy_count - 1)
        if error is not None:
            if on_error is not None:
                on_error(error)
            else:
                messagebox.showerror("PyLite Manager", str(error), parent=self)
            if completion_message is not None:
                self.set_status(completion_message)
            return

        try:
            if on_success is not None:
                on_success(result)
        finally:
            if completion_message is not None:
                self.set_status(completion_message)

    def refresh_all(self, status_message: str = "Refreshing virtual environments...") -> None:
        self.set_status("Loading global Python versions...")

        def worker():
            return detect_python_versions()

        def success(result):
            python_versions = self._prioritize_python_by_path(result)
            self.python_versions = python_versions
            self.venv_panel.set_python_versions(python_versions)
            self.refresh_virtual_environments(
                status_message=status_message,
                preserve_package_selection=False,
                auto_select_if_missing=True,
            )

        self.run_async(worker, success, status_message="Loading global Python versions...", completion_message=None)

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

    def search_virtual_environments(self) -> None:
        self.set_status("Searching virtual environments...")
        self.apply_filter()
        self.set_status("Virtual environments filtered.")

    def refresh_virtual_environments(self, status_message: str = "Searching virtual environments...", preserve_package_selection: bool = True, auto_select_if_missing: bool = True) -> None:
        selected_target = self.package_panel.get_selected_python_executable()
        selected_target_value = str(selected_target).strip().lower() if selected_target is not None else ""

        self.set_status(status_message)
        self.venv_panel.set_scan_folders(self.config_data.get("scan_folders", []))

        def worker():
            scan_roots = [Path(folder) for folder in self.config_data.get("scan_folders", [])]
            return find_venvs(scan_roots)

        def success(venvs):
            self.venvs = venvs
            self.venv_panel.set_venvs(venvs)

            if selected_target_value and preserve_package_selection and self._restore_selected_package_target(selected_target_value):
                self.set_status("Virtual environments updated.")
                return

            if auto_select_if_missing:
                self.restore_default_selection()
            else:
                self.set_status("Virtual environments updated.")

        def error(exc):
            self.set_status("Virtual environment refresh failed.")
            messagebox.showerror("PyLite Manager", f"Failed to refresh virtual environments:\n\n{exc}", parent=self)

        self.run_async(worker, success, error, status_message=status_message, completion_message=None)

    def _restore_selected_package_target(self, selected_target_value: str) -> bool:
        python_version = self._find_python_version_by_executable(selected_target_value)
        if python_version is not None:
            self.selected_python = python_version
            self.selected_python_source = "python"
            self.selected_venv = None
            return True

        venv = self._find_venv_by_python_executable(selected_target_value)
        if venv is not None:
            self.selected_venv = venv
            self.selected_python = None
            self.selected_python_source = "venv"
            return True

        return False

    def _find_python_version_by_executable(self, executable: str):
        target = str(Path(executable)).strip().lower()
        for version in self.python_versions:
            if str(Path(version.executable)).strip().lower() == target:
                return version
        return None

    def _find_venv_by_python_executable(self, executable: str):
        target = str(Path(executable)).strip().lower()
        for venv in self.venvs:
            python_executable = venv.path / "Scripts" / "python.exe"
            if str(python_executable).strip().lower() == target:
                return venv
        return None

    def add_scan_folder(self) -> None:
        folder = filedialog.askdirectory(title="Select folder to scan for virtual environments", parent=self)
        if not folder:
            return
        folders = normalize_paths(self.config_data.get("scan_folders", []) + [folder])
        self.config_data["scan_folders"] = folders
        save_config(self.config_data)
        self.venv_panel.set_scan_folders(folders)
        self.refresh_virtual_environments(status_message="Added folder. Refreshing virtual environments...", preserve_package_selection=True, auto_select_if_missing=True)

    def remove_scan_folder(self) -> None:
        folder = self.venv_panel.get_scan_folder_selection()
        if not folder:
            return
        folders = [item for item in self.config_data.get("scan_folders", []) if Path(item) != Path(folder)]
        self.config_data["scan_folders"] = folders
        save_config(self.config_data)
        self.venv_panel.set_scan_folders(folders)
        self.refresh_virtual_environments(status_message="Removed folder. Refreshing virtual environments...", preserve_package_selection=True, auto_select_if_missing=True)

    def _require_selected_python(self):
        python_executable = self.package_panel.get_selected_python_executable()
        if python_executable is None:
            messagebox.showinfo("PyLite Manager", "Select a Python version or virtual environment first.", parent=self)
            return None
        return python_executable

    def _get_selected_package_info(self):
        return self.package_panel.get_selected_package_info()

    def _require_selected_venv(self):
        venv = self.venv_panel.get_selected_venv()
        if venv is None and self.selected_venv is not None:
            return self.selected_venv
        if venv is None:
            messagebox.showinfo("PyLite Manager", "Select a virtual environment first.", parent=self)
            return None
        return venv

    def select_python_version(self, version) -> None:
        if version is None:
            return
        executable = str(Path(version.executable)).strip().lower()
        current_executable = str(self.package_panel.get_selected_python_executable()).strip().lower() if self.package_panel.get_selected_python_executable() is not None else ""
        if self.selected_python_source == "python" and self.selected_python is not None:
            if str(Path(self.selected_python.executable)).strip().lower() == executable and current_executable == executable:
                return
        self.selected_python = version
        self.selected_python_source = "python"
        label = f"Global Python | {version.display} | {version.executable}"
        self.package_panel.set_selected_target(Path(version.executable), label)
        self.refresh_packages()

    def select_venv(self, venv) -> None:
        if venv is None:
            return
        python_executable = venv.path / "Scripts" / "python.exe"
        current_executable = str(self.package_panel.get_selected_python_executable()).strip().lower() if self.package_panel.get_selected_python_executable() is not None else ""
        if self.selected_python_source == "venv" and self.selected_venv is not None:
            if str(self.selected_venv.path).strip().lower() == str(venv.path).strip().lower() and current_executable == str(python_executable).strip().lower():
                return
        self.selected_venv = venv
        self.selected_python = None
        self.selected_python_source = "venv"
        label = f"Virtual Environment | {venv.name} | {venv.path} | Python {venv.python_version}"
        self.package_panel.set_selected_target(python_executable, label)
        self.refresh_packages()

    def open_selected_folder(self, venv=None) -> None:
        if venv is None:
            venv = self._require_selected_venv()
        if venv is None:
            return
        try:
            open_folder(venv.path)
        except Exception as exc:  # pragma: no cover - UI safety
            messagebox.showerror("PyLite Manager", str(exc), parent=self)

    def open_selected_python_folder(self, version=None) -> None:
        if version is None:
            version = self.venv_panel.get_selected_python_version()
        if version is None:
            messagebox.showinfo("PyLite Manager", "Select a Python version first.", parent=self)
            return
        try:
            open_folder(Path(version.executable).parent)
        except Exception as exc:  # pragma: no cover - UI safety
            messagebox.showerror("PyLite Manager", str(exc), parent=self)

    def open_selected_python_terminal(self, version=None) -> None:
        if version is None:
            version = self.venv_panel.get_selected_python_version()
        if version is None:
            messagebox.showinfo("PyLite Manager", "Select a Python version first.", parent=self)
            return
        try:
            python_dir = Path(version.executable).parent
            open_venv_terminal(python_dir)
        except Exception as exc:  # pragma: no cover - UI safety
            messagebox.showerror("PyLite Manager", str(exc), parent=self)

    def delete_selected_python(self, version=None) -> None:
        if version is None:
            version = self.venv_panel.get_selected_python_version()
        if version is None:
            messagebox.showinfo("PyLite Manager", "Select a Python version first.", parent=self)
            return

        if not messagebox.askyesno(
            "PyLite Manager",
            f"Launch the uninstaller for this Python installation?\n\n{version.display}\n{version.executable}\n\nThis will open the installer’s uninstall flow.",
            parent=self,
        ):
            return

        self._begin_status_progress("Launching Python uninstaller...")

        def worker():
            return uninstall_python_installation(Path(version.executable))

        def success(result):
            self._end_status_progress("Python uninstaller launched.")
            messagebox.showinfo(
                "PyLite Manager",
                f"Python uninstaller launched:\n{result}\n\nComplete the uninstall in the opened window, then refresh the list.",
                parent=self,
            )

        def error(exc):
            self._end_status_progress("Failed to launch Python uninstaller.")
            messagebox.showerror("PyLite Manager", f"Failed to launch Python uninstaller:\n\n{exc}", parent=self)

        self.run_async(worker, success, error, status_message="Launching Python uninstaller...", completion_message=None)

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

    def create_virtual_environment(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Create Virtual Environment")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        python_choices = self.python_versions
        if not python_choices:
            messagebox.showinfo("PyLite Manager", "No Python versions are available to create a virtual environment.", parent=self)
            dialog.destroy()
            return

        container = ttk.Frame(dialog, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(container, text="Python version").grid(row=0, column=0, sticky=tk.W, pady=(0, 4))
        python_var = tk.StringVar(value=python_choices[0].display)
        python_combo = ttk.Combobox(container, textvariable=python_var, state="readonly", values=[item.display for item in python_choices], width=42)
        python_combo.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=(0, 8))

        ttk.Label(container, text="Venv name").grid(row=2, column=0, sticky=tk.W, pady=(0, 4))
        name_var = tk.StringVar(value="venv")
        name_entry = ttk.Entry(container, textvariable=name_var, width=44)
        name_entry.grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=(0, 8))

        ttk.Label(container, text="Location").grid(row=4, column=0, sticky=tk.W, pady=(0, 4))
        default_location = self.config_data.get("scan_folders", [str(Path.home())])[0] if self.config_data.get("scan_folders") else str(Path.home())
        location_var = tk.StringVar(value=default_location)
        location_entry = ttk.Entry(container, textvariable=location_var, width=44)
        location_entry.grid(row=5, column=0, sticky=tk.EW, pady=(0, 8))

        def browse_location() -> None:
            chosen = filedialog.askdirectory(title="Select location for the new virtual environment", parent=dialog)
            if chosen:
                location_var.set(chosen)

        browse_button = ttk.Button(container, text="Browse", command=browse_location)
        browse_button.grid(row=5, column=1, sticky=tk.E, padx=(8, 0), pady=(0, 8))

        button_row = ttk.Frame(container)
        button_row.grid(row=6, column=0, columnspan=2, sticky=tk.E, pady=(4, 0))

        selected_version: dict[str, object] = {"value": python_choices[0]}

        def on_python_change(_event=None) -> None:
            choice = python_combo.get()
            for item in python_choices:
                if item.display == choice:
                    selected_version["value"] = item
                    break

        python_combo.bind("<<ComboboxSelected>>", on_python_change)

        def close_dialog() -> None:
            dialog.grab_release()
            dialog.destroy()

        def confirm() -> None:
            on_python_change()
            chosen_version = selected_version["value"]
            venv_name = name_var.get().strip()
            location_text = location_var.get().strip()
            if not venv_name:
                messagebox.showerror("PyLite Manager", "Please enter a virtual environment name.", parent=dialog)
                return
            if not location_text:
                messagebox.showerror("PyLite Manager", "Please choose a location.", parent=dialog)
                return

            target_path = Path(location_text) / venv_name
            if target_path.exists():
                messagebox.showerror("PyLite Manager", f"This location already exists:\n\n{target_path}", parent=dialog)
                return

            self._begin_status_progress("Creating virtual environment...")

            def worker():
                return create_venv(target_path, chosen_version.spec)

            def success(_result):
                self._end_status_progress("Virtual environment created.")
                messagebox.showinfo(
                    "PyLite Manager",
                    f"Virtual environment created successfully:\n{target_path}",
                    parent=self,
                )
                close_dialog()
                self.refresh_virtual_environments(
                    status_message="Virtual environment created. Refreshing environments...",
                    preserve_package_selection=True,
                    auto_select_if_missing=True,
                )

            def error(exc):
                self._end_status_progress("Failed to create virtual environment.")
                messagebox.showerror("PyLite Manager", f"Failed to create virtual environment:\n\n{exc}", parent=dialog)

            self.run_async(worker, success, error, status_message="Creating virtual environment...", completion_message=None)

        ttk.Button(button_row, text="Cancel", command=close_dialog).pack(side=tk.RIGHT)
        ttk.Button(button_row, text="Create", command=confirm).pack(side=tk.RIGHT, padx=(0, 8))

        container.columnconfigure(0, weight=1)
        name_entry.focus_set()

    def refresh_packages(self) -> None:
        python_executable = self._require_selected_python()
        if python_executable is None:
            return

        self._package_load_token += 1
        token = self._package_load_token
        self.package_panel.begin_action_progress("Loading packages...")
        self.package_panel.set_size_loading("Calculating total size...")

        self._load_total_size_async(python_executable, token)
        self._load_package_sizes_async(python_executable, token)

        def worker():
            return list_packages(python_executable)

        def success(packages):
            if token != self._package_load_token:
                return
            self.package_panel.show_packages_iteratively(
                packages,
                on_complete=lambda: self._after_package_render(python_executable, token),
            )

        def error(exc):
            if token == self._package_load_token:
                self.package_panel.end_action_progress("Package loading failed.")
            messagebox.showerror("PyLite Manager", f"Failed to load packages:\n\n{exc}", parent=self)

        self.run_async(
            worker,
            success,
            error,
            status_message="Loading packages for selected environment...",
            completion_message="Packages loaded.",
        )

    def _after_package_render(self, python_executable: Path, token: int) -> None:
        if token != self._package_load_token:
            return
        self.package_panel.end_action_progress("Packages loaded.")
        self._apply_pending_package_sizes(token)

    def _load_total_size_async(self, python_executable: Path, token: int) -> None:
        target_root = python_executable.parent.parent if python_executable.parent.name.lower() == "scripts" else python_executable.parent

        def worker():
            return calculate_directory_size(target_root)

        def success(total_size):
            if token != self._package_load_token:
                return
            self.package_panel.set_target_size(total_size)

        self.run_async(worker, success)

    def _load_package_sizes_async(self, python_executable: Path, token: int) -> None:
        def worker():
            try:
                for name, sz in stream_package_sizes(python_executable):
                    if token != self._package_load_token:
                        break  # Stop if cancelled
                    # Schedule UI update real-time
                    self.after(0, self._apply_incremental_size, token, name, sz)
            except Exception:
                pass
            return None

        def success(_result):
            if token != self._package_load_token:
                return

        self.run_async(worker, success)

    def _apply_incremental_size(self, token: int, name: str, size: int) -> None:
        if token != self._package_load_token:
            return
        
        # Maintain cache in case the packages are still populating lazily
        if token not in self._pending_package_size_maps:
            self._pending_package_size_maps[token] = {}
        self._pending_package_size_maps[token][name] = size

        # Update UI directly
        self.package_panel.update_package_sizes({name: size})

    def _apply_pending_package_sizes(self, token: int) -> None:
        size_map = self._pending_package_size_maps.get(token)
        if not size_map:
            return
        self.package_panel.update_package_sizes(size_map)

    def open_selected_terminal(self, venv=None) -> None:
        if venv is None:
            venv = self._require_selected_venv()
        if venv is None:
            return
        try:
            open_venv_terminal(venv.path)
        except Exception as exc:  # pragma: no cover - UI safety
            messagebox.showerror("PyLite Manager", str(exc), parent=self)

    def delete_selected_venv(self, venv=None) -> None:
        if venv is None:
            venv = self._require_selected_venv()
        if venv is None:
            return
        if not messagebox.askyesno("PyLite Manager", f"Delete virtual environment?\n\n{venv.path}", parent=self):
            return

        self._begin_status_progress("Deleting virtual environment...")

        def worker():
            saved_bytes = calculate_directory_size(venv.path)
            delete_venv(venv.path)
            return venv.path, saved_bytes

        def success(result):
            deleted_path, saved_bytes = result
            self._end_status_progress("Virtual environment deleted.")
            messagebox.showinfo(
                "PyLite Manager",
                f"Deleted virtual environment:\n{deleted_path}\n\nSaved space: {format_bytes(saved_bytes)}",
                parent=self,
            )
            self.refresh_virtual_environments(
                status_message="Virtual environment deleted. Refreshing list...",
                preserve_package_selection=True,
                auto_select_if_missing=True,
            )

        def error(exc):
            self._end_status_progress("Failed to delete virtual environment.")
            messagebox.showerror("PyLite Manager", f"Failed to delete virtual environment:\n\n{exc}", parent=self)

        self.run_async(worker, success, error, status_message="Deleting virtual environment...", completion_message=None)

    def backup_selected_venv(self, venv=None) -> None:
        import shutil
        if venv is None:
            venv = self._require_selected_venv()
        if venv is None:
            return

        default_name = f"{venv.name}_backup.zip"
        save_path = filedialog.asksaveasfilename(
            parent=self,
            title="Backup Environment",
            defaultextension=".zip",
            initialfile=default_name,
            filetypes=[("Zip files", "*.zip"), ("All files", "*.*")],
        )
        if not save_path:
            return

        base_name = save_path
        if base_name.endswith('.zip'):
            base_name = base_name[:-4]

        self._begin_status_progress(f"Backing up {venv.name}...")

        def worker() -> None:
            shutil.make_archive(base_name, 'zip', str(venv.path))

        def success() -> None:
            self._end_status_progress("Backup completed.")
            messagebox.showinfo("Backup Success", f"Successfully backed up '{venv.name}'.", parent=self)

        def error(exc: Exception) -> None:
            self._end_status_progress("Backup failed.")
            messagebox.showerror("Backup Failed", str(exc), parent=self)

        self.run_async(worker, success, error)

    def clone_selected_venv(self, venv=None) -> None:
        import sys
        if venv is None:
            venv = self._require_selected_venv()
        if venv is None:
            return

        target_dir = filedialog.askdirectory(parent=self, title="Select Clone Target Directory")
        if not target_dir:
            return

        self._begin_status_progress(f"Cloning {venv.name}...")

        def worker() -> None:
            import tempfile
            from core.package_manager import export_requirements, import_requirements

            # Resolve venv python
            if sys.platform == "win32":
                src_python = venv.path / "Scripts" / "python.exe"
            else:
                src_python = venv.path / "bin" / "python"

            # Create target venv
            if sys.platform == "win32":
                create_venv(Path(target_dir), None)
            else:
                import subprocess
                subprocess.run(["python3", "-m", "venv", target_dir])

            # Export from source to temp file
            with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as tmp:
                req_file = tmp.name

            try:
                export_requirements(src_python, req_file)

                # Import to target
                if sys.platform == "win32":
                    tgt_python = Path(target_dir) / "Scripts" / "python.exe"
                else:
                    tgt_python = Path(target_dir) / "bin" / "python"

                import_requirements(tgt_python, req_file)
            finally:
                Path(req_file).unlink(missing_ok=True)

        def success() -> None:
            self._end_status_progress("Clone completed.")
            messagebox.showinfo("Clone Success", f"Successfully cloned '{venv.name}'.", parent=self)
            self.refresh_virtual_environments()

        def error(exc: Exception) -> None:
            self._end_status_progress("Clone failed.")
            messagebox.showerror("Clone Failed", str(exc), parent=self)

        self.run_async(worker, success, error)

    def upgrade_package(self, package_name: str) -> None:
        python_executable = self._require_selected_python()
        if python_executable is None:
            return

        package_info = self._get_selected_package_info()
        current_version = package_info.version if package_info is not None else ""

        if not messagebox.askyesno(
            "Upgrade Package",
            f"Update '{package_name}' from {current_version or 'current version'} to the latest version?",
            parent=self,
        ):
            return

        self.package_panel.begin_action_progress(f"Upgrading {package_name}...")

        def worker():
            pkg_upgrade(python_executable, package_name)
            return current_version, get_package_version(python_executable, package_name)

        def success(result):
            before_version, new_version = result
            self.package_panel.end_action_progress("Upgrade complete.")
            if not new_version:
                messagebox.showerror(
                    "Upgrade Failed",
                    f"{package_name} was upgraded, but the installed version could not be confirmed.",
                    parent=self,
                )
                self.refresh_packages()
                return
            if before_version and new_version == before_version:
                messagebox.showinfo(
                    "Upgrade Result",
                    f"{package_name} is already at version {new_version}.",
                    parent=self,
                )
                self.refresh_packages()
                return
            messagebox.showinfo(
                "Upgrade Complete",
                f"'{package_name}' upgraded from {before_version or 'unknown'} to {new_version}.",
                parent=self,
            )
            self.refresh_packages()

        def error(exc):
            self.package_panel.end_action_progress("Upgrade failed.")
            messagebox.showerror("Upgrade Failed", f"Failed to upgrade {package_name}:\n\n{exc}", parent=self)
            self.refresh_packages()

        self.run_async(worker, success, error)

    def export_requirements(self) -> None:
        python_executable = self._require_selected_python()
        if python_executable is None:
            return

        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Export requirements.txt",
            defaultextension=".txt",
            initialfile="requirements.txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not file_path:
            return

        def worker() -> None:
            pkg_export(python_executable, file_path)

        def error(exc: Exception) -> None:
            messagebox.showerror("Export Failed", str(exc), parent=self)

        def success() -> None:
            messagebox.showinfo(
                "Export Success",
                f"Successfully exported requirements to {Path(file_path).name}.",
                parent=self,
            )

        self.run_async(worker, success, error)

    def import_requirements(self) -> None:
        python_executable = self._require_selected_python()
        if python_executable is None:
            return

        file_path = filedialog.askopenfilename(
            parent=self,
            title="Import requirements.txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not file_path:
            return

        def worker() -> None:
            pkg_import(python_executable, file_path)

        def error(exc: Exception) -> None:
            messagebox.showerror("Import Failed", str(exc), parent=self)

        def success() -> None:
            messagebox.showinfo(
                "Import Success",
                f"Successfully imported requirements from {Path(file_path).name}.",
                parent=self,
            )
            self.refresh_packages()

        self.run_async(worker, success, error)

    def show_package_stats(self) -> None:
        python_executable = self._require_selected_python()
        if python_executable is None:
            return

        all_packages = self.package_panel._all_packages
        if not all_packages:
            messagebox.showinfo("Package Stats", "No packages loaded or environment is empty.", parent=self)
            return

        total_count = len(all_packages)
        total_bytes = sum(getattr(pkg, "size_bytes", 0) for pkg in all_packages)

        stats_message = (
            f"Package Statistics\n"
            f"------------------\n"
            f"Total Packages: {total_count}\n"
            f"Total Size: {format_bytes(total_bytes)}\n\n"
            f"Target: {python_executable}"
        )

        messagebox.showinfo("Package Stats", stats_message, parent=self)

    def degrade_package(self, package_name: str) -> None:
        python_executable = self._require_selected_python()
        if python_executable is None:
            return

        package_info = self._get_selected_package_info()
        current_version = package_info.version if package_info is not None else ""
        target_version = simpledialog.askstring(
            "Downgrade Package",
            f"Enter the version to install for '{package_name}' (current: {current_version or 'unknown'}):",
            parent=self,
        )
        if not target_version:
            return

        self.package_panel.begin_action_progress(f"Installing {package_name}=={target_version}...")

        def worker():
            pkg_install(python_executable, f"{package_name}=={target_version}")
            return current_version, get_package_version(python_executable, package_name)

        def success(result):
            before_version, new_version = result
            self.package_panel.end_action_progress("Downgrade complete.")
            if not new_version:
                messagebox.showerror(
                    "Downgrade Failed",
                    f"{package_name} was installed, but the version could not be confirmed.",
                    parent=self,
                )
                self.refresh_packages()
                return
            if new_version != target_version:
                messagebox.showerror(
                    "Downgrade Failed",
                    f"Requested {package_name}=={target_version}, but the installed version is {new_version}.",
                    parent=self,
                )
                self.refresh_packages()
                return
            messagebox.showinfo(
                "Downgrade Complete",
                f"'{package_name}' changed from {before_version or 'unknown'} to {new_version}.",
                parent=self,
            )
            self.refresh_packages()

        def error(exc):
            self.package_panel.end_action_progress("Downgrade failed.")
            messagebox.showerror(
                "Downgrade Failed",
                f"Failed to install {package_name}=={target_version}:\n\n{exc}",
                parent=self,
            )
            self.refresh_packages()

        self.run_async(worker, success, error)

    def uninstall_package(self, package_name: str) -> None:
        python_executable = self._require_selected_python()
        if python_executable is None:
            return
        if not messagebox.askyesno(
            "Uninstall Package",
            f"Are you sure you want to uninstall '{package_name}'?",
            parent=self,
        ):
            return

        self.status_var.set(f"Uninstalling {package_name}...")
        self.package_panel.set_loading(f"Uninstalling {package_name}...")

        def worker():
            pkg_uninstall(python_executable, package_name)
            return package_name

        def success(result):
            messagebox.showinfo(
                "Package Removed",
                f"'{result}' was successfully uninstalled.",
                parent=self,
            )
            self.status_var.set(f"Uninstalled {package_name}")
            self.refresh_packages()

        def error(exc):
            self.status_var.set(f"Error uninstalling {package_name}")
            messagebox.showerror("Uninstall Failed", f"Failed to uninstall {package_name}:\n\n{exc}", parent=self)
            self.refresh_packages()

        self.run_async(worker, success, error)

