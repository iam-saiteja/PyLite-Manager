from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import ttk


class VenvPanel(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, padding=12)

        self._python_lookup: dict[str, object] = {}
        self._venv_lookup: dict[str, object] = {}
        self._scan_folders: list[str] = []
        self._python_select_callback = None
        self._venv_select_callback = None
        self._open_folder_callback = None
        self._delete_venv_callback = None
        self._open_python_folder_callback = None
        self._context_venv = None
        self._context_python = None
        self._remove_scan_folder_callback = None

        environments_section = ttk.LabelFrame(self, text="Environments")
        environments_section.pack(fill=tk.BOTH, expand=True)

        versions_section = ttk.LabelFrame(environments_section, text="Python versions")
        versions_section.pack(fill=tk.BOTH, expand=False, pady=(0, 10))

        self.python_tree = ttk.Treeview(versions_section, columns=("Version", "Path", "Default"), show="headings", height=4)
        self.python_tree.heading("Version", text="Version")
        self.python_tree.heading("Path", text="Path")
        self.python_tree.heading("Default", text="Default")
        self.python_tree.column("Version", width=100, anchor=tk.W)
        self.python_tree.column("Path", width=220, anchor=tk.W)
        self.python_tree.column("Default", width=70, anchor=tk.CENTER)
        self.python_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        python_xscroll = ttk.Scrollbar(versions_section, orient=tk.HORIZONTAL, command=self.python_tree.xview)
        self.python_tree.configure(xscrollcommand=python_xscroll.set)
        python_xscroll.pack(fill=tk.X, padx=8, pady=(0, 8))

        self.set_default_button = ttk.Button(versions_section, text="Set Default")
        self.set_default_button.pack(anchor=tk.W, padx=8, pady=(0, 8))

        folders_section = ttk.LabelFrame(environments_section, text="Scan folders")
        folders_section.pack(fill=tk.X, pady=(0, 10))

        folders_body = ttk.Frame(folders_section)
        folders_body.pack(fill=tk.X, padx=8, pady=8)

        self.scan_list = tk.Listbox(folders_body, height=3, activestyle="dotbox")
        self.scan_list.grid(row=0, column=0, rowspan=3, sticky="nsew", padx=(0, 8))

        scan_xscroll = ttk.Scrollbar(folders_body, orient=tk.HORIZONTAL, command=self.scan_list.xview)
        self.scan_list.configure(xscrollcommand=scan_xscroll.set)
        scan_xscroll.grid(row=3, column=0, sticky="ew", padx=(0, 8))

        folder_buttons = ttk.Frame(folders_body)
        folder_buttons.grid(row=0, column=1, sticky="ne")

        self.add_folder_button = ttk.Button(folder_buttons, text="Add")
        self.add_folder_button.pack(fill=tk.X, pady=(0, 4))
        self.refresh_button = ttk.Button(folder_buttons, text="Refresh")
        self.refresh_button.pack(fill=tk.X, pady=(4, 0))

        self.scan_menu = tk.Menu(self, tearoff=0)
        self.scan_menu.add_command(label="Delete", command=self._delete_selected_scan_folder)

        folders_body.columnconfigure(0, weight=1)

        venv_section = ttk.LabelFrame(environments_section, text="Virtual environments")
        venv_section.pack(fill=tk.BOTH, expand=True)

        search_frame = ttk.Frame(venv_section)
        search_frame.pack(fill=tk.X, padx=8, pady=(8, 0))
        ttk.Label(search_frame, text="Search").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8))
        self.create_button = ttk.Button(search_frame, text="New Venv")
        self.create_button.pack(side=tk.RIGHT)

        self.venv_tree = ttk.Treeview(venv_section, columns=("Name", "Path", "Python"), show="headings", height=10)
        for heading, width in (("Name", 140), ("Path", 350), ("Python", 100)):
            self.venv_tree.heading(heading, text=heading)
            self.venv_tree.column(heading, width=width, anchor=tk.W)
        self.venv_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        venv_xscroll = ttk.Scrollbar(venv_section, orient=tk.HORIZONTAL, command=self.venv_tree.xview)
        self.venv_tree.configure(xscrollcommand=venv_xscroll.set)
        venv_xscroll.pack(fill=tk.X, padx=8, pady=(0, 8))

        self.venv_menu = tk.Menu(self, tearoff=0)
        self.venv_menu.add_command(label="Open Folder", command=self._open_selected_venv_folder)
        self.venv_menu.add_separator()
        self.venv_menu.add_command(label="Delete", command=self._delete_selected_venv)

        self.python_menu = tk.Menu(self, tearoff=0)
        self.python_menu.add_command(label="Open Folder", command=self._open_selected_python_folder)

        self.python_tree.bind("<<TreeviewSelect>>", self._on_python_select)
        self.python_tree.bind("<ButtonPress-3>", self._on_python_right_click)
        self.venv_tree.bind("<<TreeviewSelect>>", self._on_select)
        self.venv_tree.bind("<ButtonPress-3>", self._on_venv_right_click)
        self.scan_list.bind("<Button-3>", self._on_scan_right_click)
        self.search_var.trace_add("write", lambda *_: None)

    def set_actions(self, add_folder_callback, remove_folder_callback, refresh_callback, search_callback, set_default_callback, create_callback) -> None:
        self.add_folder_button.configure(command=add_folder_callback)
        self._remove_scan_folder_callback = remove_folder_callback
        self.refresh_button.configure(command=refresh_callback)
        self.set_default_button.configure(command=set_default_callback)
        self.create_button.configure(command=create_callback)
        self.search_var.trace_add("write", lambda *_: search_callback())

    def set_venv_context_actions(self, open_folder_callback) -> None:
        self._open_folder_callback = open_folder_callback

    def set_venv_delete_action(self, delete_venv_callback) -> None:
        self._delete_venv_callback = delete_venv_callback

    def set_python_context_actions(self, open_folder_callback) -> None:
        self._open_python_folder_callback = open_folder_callback

    def set_selection_callbacks(self, python_callback, venv_callback) -> None:
        self._python_select_callback = python_callback
        self._venv_select_callback = venv_callback

    def set_scan_folders(self, folders: list[str]) -> None:
        self._scan_folders = folders
        self.scan_list.delete(0, tk.END)
        for folder in folders:
            self.scan_list.insert(tk.END, folder)

    def get_scan_folder_selection(self) -> str:
        selection = self.scan_list.curselection()
        if not selection:
            return ""
        return str(self.scan_list.get(selection[0]))

    def get_search_text(self) -> str:
        return self.search_var.get().strip().lower()

    def set_python_versions(self, versions) -> None:
        self._python_lookup = {}
        for item in self.python_tree.get_children():
            self.python_tree.delete(item)
        for version in versions:
            item_id = self.python_tree.insert(
                "",
                tk.END,
                values=(version.display, version.executable, "Yes" if getattr(version, "is_default", False) else ""),
            )
            self._python_lookup[item_id] = version

    def set_venvs(self, venvs) -> None:
        self._venv_lookup = {}
        for item in self.venv_tree.get_children():
            self.venv_tree.delete(item)
        filter_text = self.get_search_text()
        for venv in venvs:
            if filter_text and filter_text not in venv.name.lower() and filter_text not in str(venv.path).lower():
                continue
            item_id = self.venv_tree.insert("", tk.END, values=(venv.name, str(venv.path), venv.python_version))
            self._venv_lookup[item_id] = venv

    def get_selected_venv(self):
        selection = self.venv_tree.selection()
        if not selection:
            return None
        return self._venv_lookup.get(selection[0])

    def get_selected_python_version(self):
        selection = self.python_tree.selection()
        if not selection:
            return None
        return self._python_lookup.get(selection[0])

    def _on_select(self, _event=None) -> None:
        selection = self.venv_tree.selection()
        if not selection:
            return
        venv = self._venv_lookup.get(selection[0])
        if self._venv_select_callback is not None:
            self._venv_select_callback(venv)

    def _on_venv_right_click(self, event: tk.Event) -> None:
        row_id = self.venv_tree.identify_row(event.y)
        if not row_id:
            return "break"
        self._context_venv = self._venv_lookup.get(row_id)
        self.venv_menu.post(event.x_root, event.y_root)
        return "break"

    def _on_scan_right_click(self, event: tk.Event) -> None:
        index = self.scan_list.nearest(event.y)
        if index < 0:
            return
        self.scan_list.selection_clear(0, tk.END)
        self.scan_list.selection_set(index)
        self.scan_menu.post(event.x_root, event.y_root)

    def _on_python_right_click(self, event: tk.Event) -> None:
        row_id = self.python_tree.identify_row(event.y)
        if not row_id:
            return "break"
        self._context_python = self._python_lookup.get(row_id)
        self.python_menu.post(event.x_root, event.y_root)
        return "break"

    def _open_selected_venv_folder(self) -> None:
        if self._open_folder_callback is not None and self._context_venv is not None:
            self._open_folder_callback(self._context_venv)

    def _delete_selected_venv(self) -> None:
        if self._delete_venv_callback is not None and self._context_venv is not None:
            self._delete_venv_callback(self._context_venv)

    def _open_selected_python_folder(self) -> None:
        if self._open_python_folder_callback is not None and self._context_python is not None:
            self._open_python_folder_callback(self._context_python)

    def _delete_selected_scan_folder(self) -> None:
        if self._remove_scan_folder_callback is not None:
            self._remove_scan_folder_callback()

    def _on_python_select(self, _event=None) -> None:
        selection = self.python_tree.selection()
        if not selection:
            return
        version = self._python_lookup.get(selection[0])
        if self._python_select_callback is not None:
            self._python_select_callback(version)
