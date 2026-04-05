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

        header = ttk.Frame(self)
        header.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(header, text="Selected Python", style="Section.TLabel").pack(anchor=tk.W)
        self.details_var = tk.StringVar(value="No Python target selected")
        ttk.Label(header, textvariable=self.details_var, wraplength=560).pack(anchor=tk.W, pady=(4, 0))

        self.size_var = tk.StringVar(value="")
        ttk.Label(header, textvariable=self.size_var, wraplength=560).pack(anchor=tk.W, pady=(2, 0))

        self.loading_var = tk.StringVar(value="Select a Python target to load packages")
        self.loading_label = ttk.Label(self, textvariable=self.loading_var, anchor=tk.CENTER)
        self.loading_label.pack(fill=tk.X, pady=(0, 8))

        self.tree = ttk.Treeview(self, columns=("Name", "Version", "Size"), show="headings", height=18)
        for heading, width in (("Name", 260), ("Version", 120), ("Size", 100)):
            self.tree.heading(heading, text=heading)
            self.tree.column(heading, width=width, anchor=tk.W)
        self.tree.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.place(relx=1.0, rely=0.22, relheight=0.78, anchor="ne")

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def set_selected_target(self, python_executable: Path | None, label: str = "") -> None:
        self._selected_python_executable = python_executable
        if python_executable is None:
            self.details_var.set("No Python target selected")
            self.loading_var.set("Select a Python target to load packages")
            self.size_var.set("")
        else:
            self.details_var.set(label)
            self.loading_var.set("Loading packages...")
            self.size_var.set("Calculating total size...")
        self.clear_packages()

    def get_selected_python_executable(self) -> Path | None:
        return self._selected_python_executable

    def get_selected_package_name(self) -> str:
        return self._selected_package_name

    def set_loading(self, message: str = "Loading packages...") -> None:
        self.loading_var.set(message)

    def set_target_size(self, byte_count: int) -> None:
        self.size_var.set(f"Total size: {format_bytes(byte_count)}")

    def show_packages_iteratively(self, packages, chunk_size: int = 5, delay_ms: int = 10) -> None:
        self.clear_packages()
        package_list = list(packages)
        if not package_list:
            self.loading_var.set("No packages found")
            return

        self.loading_var.set(f"Loading {len(package_list)} packages...")

        def insert_chunk(start_index: int) -> None:
            end_index = min(start_index + chunk_size, len(package_list))
            for item in package_list[start_index:end_index]:
                self.tree.insert("", tk.END, values=(item.name, item.version, format_bytes(getattr(item, "size_bytes", 0))))

            if end_index < len(package_list):
                self.loading_var.set(f"Loaded {end_index}/{len(package_list)} packages...")
                self.after(delay_ms, lambda: insert_chunk(end_index))
            else:
                self.loading_var.set(f"Loaded {len(package_list)} packages")

        self.after(0, lambda: insert_chunk(0))

    def clear_packages(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._selected_package_name = ""

    def _on_select(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            self._selected_package_name = ""
            return
        values = self.tree.item(selection[0], "values")
        self._selected_package_name = values[0] if values else ""
