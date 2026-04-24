from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import ttk

from utils.helpers import format_bytes


class PackagePanel(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, padding=12)

        self._selected_python_executable: Path | None = None
        self._selected_package_name: str = ""
        self._row_ids_by_name: dict[str, list[str]] = {}

        header = ttk.Frame(self)
        header.pack(fill=tk.X, pady=(0, 8))

        top_header = ttk.Frame(header)
        top_header.pack(fill=tk.X)
        ttk.Label(top_header, text="Selected Python", style="Section.TLabel").pack(side=tk.LEFT)

        # Refresh / Search
        self.refresh_btn = ttk.Button(top_header, text="\u21bb Refresh", state=tk.DISABLED)
        self.refresh_btn.pack(side=tk.RIGHT)

        self.export_btn = ttk.Button(top_header, text="Export", state=tk.DISABLED)
        self.export_btn.pack(side=tk.RIGHT, padx=(5, 0))

        self.import_btn = ttk.Button(top_header, text="Import", state=tk.DISABLED)
        self.import_btn.pack(side=tk.RIGHT, padx=(5, 0))

        self.stats_btn = ttk.Button(top_header, text="Stats", state=tk.DISABLED)
        self.stats_btn.pack(side=tk.RIGHT, padx=(10, 0))

        search_frame = ttk.Frame(top_header)
        search_frame.pack(side=tk.RIGHT, padx=(10, 0))
        search_frame.pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search_change)
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=20, state=tk.DISABLED)
        self.search_entry.pack(side=tk.LEFT)

        self.details_var = tk.StringVar(value="No Python target selected")
        ttk.Label(header, textvariable=self.details_var, wraplength=560).pack(anchor=tk.W, pady=(4, 0))

        self.size_var = tk.StringVar(value="")
        ttk.Label(header, textvariable=self.size_var, wraplength=560).pack(anchor=tk.W, pady=(2, 0))

        self.loading_var = tk.StringVar(value="Select a Python target to load packages")
        self.loading_label = ttk.Label(self, textvariable=self.loading_var, anchor=tk.CENTER)
        self.loading_label.pack(fill=tk.X, pady=(0, 8))

        self.action_progress = ttk.Progressbar(self, mode="indeterminate")
        self.action_progress.pack(fill=tk.X, pady=(0, 8))
        self.action_progress.stop()
        self.action_progress.pack_forget()

        # Context Menu for TreeView
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Update to Latest", command=self._on_update_clicked)
        self.context_menu.add_command(label="Degrade / Install Specific Version", command=self._on_degrade_clicked)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Delete / Uninstall", command=self._on_delete_clicked)

        self.tree = ttk.Treeview(self, columns=("Name", "Version", "Size"), show="headings", height=18)
        self.tree.bind("<Button-3>", self._on_right_click)

        for heading, width in (("Name", 260), ("Version", 120), ("Size", 100)):
            self.tree.heading(heading, text=heading)
            self.tree.column(heading, width=width, anchor=tk.W)
        self.tree.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.place(relx=1.0, rely=0.22, relheight=0.78, anchor="ne")

        xscrollbar = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(xscrollcommand=xscrollbar.set)
        xscrollbar.pack(fill=tk.X, pady=(0, 8))

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        self._all_packages = []
        self._on_refresh_callback = None
        self._on_update_callback = None
        self._on_degrade_callback = None
        self._on_delete_callback = None
        self._render_token = 0
        self._search_timer = None
        self._action_progress_visible = False

    def set_callbacks(self, on_refresh=None, on_install=None, on_update=None, on_degrade=None, on_delete=None, on_export=None, on_import=None, on_stats=None) -> None:
        self._on_refresh_callback = on_refresh
        self._on_update_callback = on_update
        self._on_degrade_callback = on_degrade
        self._on_delete_callback = on_delete
        self._on_stats_callback = on_stats

        if on_refresh:
            self.refresh_btn.config(command=on_refresh, state=tk.NORMAL)
        if on_export:
            self.export_btn.config(command=on_export, state=tk.NORMAL)
        if on_import:
            self.import_btn.config(command=on_import, state=tk.NORMAL)
        if on_stats:
            self.stats_btn.config(command=on_stats, state=tk.NORMAL)

    def _on_search_change(self, *args) -> None:
        if not self._all_packages:
            return
        if self._search_timer:
            self.after_cancel(self._search_timer)
        self._search_timer = self.after(200, self._apply_search)

    def _apply_search(self) -> None:
        if not self._all_packages:
            return
        query = self.search_var.get().lower()
        if not query:
            self.show_packages_iteratively(self._all_packages, chunk_size=30, is_search=True)
            return

        filtered = [pkg for pkg in self._all_packages if query in pkg.name.lower()]
        self.show_packages_iteratively(filtered, chunk_size=30, is_search=True)

    def _on_right_click(self, event: tk.Event) -> None:
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self._selected_package_name = self.tree.item(item, "values")[0]
            self.context_menu.post(event.x_root, event.y_root)

    def _on_update_clicked(self) -> None:
        if self._on_update_callback and self._selected_package_name:
            self._on_update_callback(self._selected_package_name)

    def _on_degrade_clicked(self) -> None:
        if self._on_degrade_callback and self._selected_package_name:
            self._on_degrade_callback(self._selected_package_name)

    def _on_delete_clicked(self) -> None:
        if self._on_delete_callback and self._selected_package_name:
            self._on_delete_callback(self._selected_package_name)

    def set_selected_target(self, python_executable: Path | None, label: str = "") -> None:
        self._selected_python_executable = python_executable
        if python_executable is None:
            self.details_var.set("No Python target selected")
            self.loading_var.set("Select a Python target to load packages")
            self.size_var.set("")
            self.search_entry.config(state=tk.DISABLED)
            self.refresh_btn.config(state=tk.DISABLED)
            self.export_btn.config(state=tk.DISABLED)
            self.import_btn.config(state=tk.DISABLED)
            self.stats_btn.config(state=tk.DISABLED)
        else:
            self.details_var.set(label)
            self.loading_var.set("Loading packages...")
            self.size_var.set("Calculating total size...")
            self.search_entry.config(state=tk.NORMAL)
            self.refresh_btn.config(state=tk.NORMAL)
            self.export_btn.config(state=tk.NORMAL)
            self.import_btn.config(state=tk.NORMAL)
            self.stats_btn.config(state=tk.NORMAL)
        self.clear_packages()
        self._all_packages.clear()
        self.search_var.set("")

    def get_selected_python_executable(self) -> Path | None:
        return self._selected_python_executable

    def get_selected_package_name(self) -> str:
        return self._selected_package_name

    def get_selected_package_info(self):
        if not self._selected_package_name:
            return None
        for package in self._all_packages:
            if package.name.lower() == self._selected_package_name.lower():
                return package
        return None

    def set_loading(self, message: str = "Loading packages...") -> None:
        self.loading_var.set(message)

    def begin_action_progress(self, message: str) -> None:
        self.loading_var.set(message)
        if not self._action_progress_visible:
            self.action_progress.pack(fill=tk.X, pady=(0, 8), before=self.tree)
            self._action_progress_visible = True
        self.action_progress.start(12)

    def end_action_progress(self, message: str = "Packages loaded.") -> None:
        self.action_progress.stop()
        if self._action_progress_visible:
            self.action_progress.pack_forget()
            self._action_progress_visible = False
        self.loading_var.set(message)

    def set_size_loading(self, message: str = "Calculating total size...") -> None:
        self.size_var.set(message)

    def set_target_size(self, byte_count: int) -> None:
        self.size_var.set(f"Total size: {format_bytes(byte_count)}")

    def show_packages_iteratively(self, packages, chunk_size: int = 5, delay_ms: int = 10, on_complete=None, is_search: bool = False) -> None:
        self._render_token += 1
        current_token = self._render_token

        if not is_search:
            self._all_packages = list(packages)

        self.clear_packages()
        package_list = list(packages)
        if not package_list:
            if is_search:
                self.loading_var.set("No packages match your search")
            else:
                self.loading_var.set("No packages found")
            if on_complete is not None:
                self.after(0, on_complete)
            return

        if not is_search:
            self.loading_var.set(f"Loading {len(package_list)} packages...")

        def insert_chunk(start_index: int) -> None:
            if current_token != self._render_token:
                return  # Another render started
            
            end_index = min(start_index + chunk_size, len(package_list))
            for i, item in enumerate(package_list[start_index:end_index], start=start_index):
            for i, item in enumerate(package_list[start_index:end_index], start=start_index):
                size_str = format_bytes(item.size_bytes) if getattr(item, "size_bytes", 0) > 0 else "..."
                tag = "even" if i % 2 == 0 else "odd"
                row_id = self.tree.insert("", tk.END, values=(item.name, item.version, size_str), tags=(tag,))
                tag = "even" if i % 2 == 0 else "odd"
                row_id = self.tree.insert("", tk.END, values=(item.name, item.version, size_str), tags=(tag,))
                self._row_ids_by_name.setdefault(item.name.lower(), []).append(row_id)

            self.tree.tag_configure("even", background="#ffffff")
            self.tree.tag_configure("odd", background="#f9f9f9")

            self.tree.tag_configure("even", background="#ffffff")
            self.tree.tag_configure("odd", background="#f9f9f9")

            if end_index < len(package_list):
                if not is_search:
                    self.loading_var.set(f"Loaded {end_index}/{len(package_list)} packages...")
                self.after(delay_ms, lambda: insert_chunk(end_index))
            else:
                if is_search:
                    total_loaded = len(self._all_packages)
                    self.loading_var.set(f"Showing {len(package_list)} of {total_loaded} packages")
                else:
                    self.loading_var.set(f"Loaded {len(package_list)} packages")
                if on_complete is not None:
                    self.after(0, on_complete)

        self.after(0, lambda: insert_chunk(0))

    def update_package_sizes(self, size_map: dict[str, int]) -> None:
        for pkg in self._all_packages:
            if pkg.name in size_map:
                pkg.size_bytes = size_map[pkg.name]
                
        for package_name, package_size in size_map.items():
            for row_id in self._row_ids_by_name.get(package_name.lower(), []):
                if not self.tree.exists(row_id):
                    continue
                values = list(self.tree.item(row_id, "values"))
                if len(values) == 3:
                    values[2] = format_bytes(package_size)
                    self.tree.item(row_id, values=values)

    def clear_packages(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._selected_package_name = ""
        self._row_ids_by_name = {}

    def _on_select(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            self._selected_package_name = ""
            return
        values = self.tree.item(selection[0], "values")
        self._selected_package_name = values[0] if values else ""
