# PyLite Manager

PyLite Manager is a lightweight Windows desktop app for managing Python installations, virtual environments, and installed packages.

## Features

- Detects Python installations registered with the Windows Python Launcher
- Finds virtual environments across configured folders
- Lists installed packages with versions and sizes
- Supports package search, update, downgrade, and uninstall
- Set a selected Python as the default in your PATH
- Responsive UI with background operations

## Requirements

- Windows 7 or later
- Python 3.9 or higher
- tkinter and pip

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd PyLite_Manager
   ```

2. Run the app:
   ```bash
   python main.py
   ```

## Usage

1. Run `python main.py`
2. Select a Python or virtual environment in the left panel
3. View and manage packages in the right panel
4. Add scan folders to discover more virtual environments

## Configuration

Settings are stored in `%LOCALAPPDATA%\PyLite_Manager\config.json`:

- `scan_folders`: directories to search for virtual environments
- `default_python_path`: the last Python path set as default

## Project Structure

- `main.py` — entry point
- `core/` — Python detection, venv management, package management, PATH handling
- `ui/` — UI components
- `utils/` — helpers and configuration

## Troubleshooting

- If no Python versions appear, verify `py --version` works in Command Prompt
- If a virtual environment is missing, add its parent folder to scan folders and refresh
- If the app won't start, delete the config file and try again

A comprehensive, lightweight desktop application for managing Python environments, virtual environments, and packages on Windows. PyLite Manager provides an intuitive graphical interface to discover, organize, and maintain multiple Python installations and virtual environments with real-time package management capabilities.

## Table of Contents

- [Features](#features)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [User Interface](#user-interface)
- [Features in Detail](#features-in-detail)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [Troubleshooting](#troubleshooting)
- [Contributors](#contributors)
- [License](#license)

## Features

### Python Version Management
- **Automatic Detection**: Discovers all Python installations registered with the Windows Python Launcher (`py` command)
- **Display Detailed Info**: Shows Python version, executable path, and default status
- **Set Default**: Easily prioritize a Python version in your system PATH
- **Open Installation Folder**: Quick access to Python installation directories
- **Smart Path Management**: Automatically positions your selected Python at the top of the user PATH environment variable

### Virtual Environment Management
- **Smart Discovery**: Finds virtual environments across multiple directories with layout-based detection (supports both Windows and Unix-style venv structures)
- **Custom Folder Support**: Detects venvs in folders with any naming convention, not just standard names
- **Flexible Scanning**: Add multiple scan directories to search for virtual environments
- **Create New Environments**: Built-in venv creation with configurable Python version, name, and location
- **Environment Details**: View Python version for each environment
- **Folder Navigation**: Quick access to environment directories
- **Secure Deletion**: Delete environments with progress tracking and saved-space confirmation

### Package Management
- **Real-Time Package Discovery**: Lists all installed packages with versions and sizes
- **Incremental Loading**: Packages load progressively to keep the UI responsive
- **Fast Search**: Debounced search with real-time filtering across 1000+ packages
- **Size Tracking**: Calculate and display individual package sizes and total environment size
- **Update Packages**: Upgrade packages to their latest versions
- **Version Control**: Install specific package versions or downgrade to previous releases
- **Safe Removal**: Uninstall packages with confirmation and status feedback
- **Progress Indicators**: Visual feedback with progress bars for long-running operations

### User Experience
- **Responsive Design**: Non-blocking operations with background threading
- **Resizable Panels**: Adjustable split view between environments (left) and packages (right)
- **Horizontal Scrolling**: Access wide content in compact layouts
- **Smart Selection**: Re-selecting the same target doesn't trigger unnecessary reloads
- **Context Menus**: Right-click options for quick actions without changing selection
- **Status Bar**: Real-time operation status with progress indicators
- **Confirmation Dialogs**: Safety confirmations with detailed operation info

### System Integration
- **Environment Variable Management**: Direct manipulation of Windows PATH registry
- **Registry Broadcasting**: Automatic environment variable updates reflected system-wide
- **Windows Explorer Integration**: Open folders in File Explorer from the application
- **Persistent Configuration**: Saves scan folders and preferences across sessions

---

## System Requirements

- **Operating System**: Windows 7 or later (Windows 10/11 recommended)
- **Python Version**: Python 3.9 or higher
- **Dependencies**: tkinter (included with Python on Windows), pip
- **Disk Space**: ~10 MB for the application
- **Permissions**: User-level access required; administrator access recommended for system PATH modifications

---

## Installation

### Method 1: From Source (Recommended)

1. Clone or download the repository:
   ```bash
   git clone <repository-url>
   cd PyLite_Manager
   ```

2. Ensure Python 3.9+ is installed and available in PATH

3. Run the application:
   ```bash
   python main.py
   ```

### Method 2: Standalone Executable

If a compiled `.exe` is available:
1. Download the built executable (`PyLite_Manager.exe`)
2. Open it from the `dist/` folder
3. Application data will be stored in `%LOCALAPPDATA%\PyLite_Manager\`

### Method 3: Create a Desktop Shortcut

Create a `.bat` file to launch the application:
```batch
@echo off
cd /d "C:\Path\To\PyLite_Manager"
python main.py
pause
```

---

## Quick Start

### First Launch

1. **Run the Application**
   - Launch with `python main.py` or double-click the executable

2. **View Python Versions**
   - The top-left panel automatically displays all detected Python installations
   - Each entry shows: Version number, installation path, and default status

3. **Add Scan Folders**
   - Click **Add** in the Scan Folders section
   - Select a directory to recursively search for virtual environments
   - Click **Refresh** to scan for new environments

4. **Select a Python or Environment**
   - Click on any Python version or virtual environment
   - The right panel loads all installed packages
   - Scroll through packages or use Search to find specific ones

5. **Manage Packages**
   - Right-click a package to:
     - Update to the latest version
     - Downgrade to a specific version
     - Uninstall the package

---

## User Interface

### Layout

The application uses a **split-pane layout**:

#### Left Pane: Environments
- **Python Versions**: Automatically detected global Python installations
- **Scan Folders**: Directories to search for virtual environments
- **Virtual Environments**: All discovered venvs with search filtering
- **Buttons**:
  - Set Default: Make selected Python the default
  - New Venv: Create a new virtual environment
  - Add/Refresh: Manage scan folders

#### Right Pane: Packages
- **Header**: Shows selected Python/environment with its total package size
- **Search & Refresh**: Filter packages or reload the list
- **Package List**: Name, version, and size columns
- **Context Menu**: Right-click for package actions

#### Status Bar
- Real-time operation status
- Progress indicator for long-running tasks

### Interactions

**Left-Click Selection**
- Selects an item and loads its packages on the right

**Right-Click Context Menu**
- Opens action menu without changing current selection
- Global Python: Open folder only
- Virtual Environment: Open folder or delete
- Packages: Update, downgrade, or uninstall

**Search**
- Type in the venv search box to filter environments by name or path
- Type in the package search box to filter packages by name
- Both support partial matching and are case-insensitive

---

## Features in Detail

### Global Python Management

#### Discovering Python Versions
PyLite Manager uses the Windows Python Launcher (`py -0p`) to detect all installed Python versions. This includes:
- Official Python.org releases
- Microsoft Store Python installations
- Conda/Anaconda Python environments
- Custom Python builds

**Display Format**: `[Version] [Path] [Default Status]`
- Version: e.g., "3.12.1"
- Path: Full executable path
- Default: "Yes" if set as system default

#### Setting Default Python
Clicking "Set Default" performs these actions:
1. Extracts the Python directory and Scripts subdirectory
2. Adds both to the top of your user PATH
3. Removes duplicate PATH entries
4. Broadcasts environment change to all running applications

Result: `python`, `pip`, and other commands now use this version by default.

#### Uninstalling Global Python
Right-click menu includes delete option (for future versions). Current behavior:
- Searches for an uninstaller executable near the Python installation
- Launches the official uninstaller if found
- Displays error if no uninstaller is available

### Virtual Environment Discovery

#### Advanced Detection Algorithm
PyLite Manager uses multiple detection strategies to find virtual environments:

1. **Standard Marker**: Presence of `pyvenv.cfg` file
2. **Windows Layout**: Scripts/python.exe + site-packages
3. **Unix Layout**: bin/python + lib/site-packages
4. **Fallback Detection**: Directory structure analysis for custom-named environments

#### Search Scope
- Recursively scans all directories under each configured scan folder
- Ignores common non-venv directories: `.git`, `node_modules`, `__pycache__`, etc.
- Deduplicates by resolved path to avoid listing symlinks twice

#### Creating New Environments
The **New Venv** dialog provides:
- **Python Selection**: Choose which detected Python version to use
- **Environment Name**: Set a custom name for the environment
- **Location**: Select where to create the environment
- **Progress Feedback**: Real-time status updates during creation

### Package Management

#### Package Loading
When an environment is selected:
1. Lists all installed packages using `pip list --format=json`
2. Calculates package sizes using `importlib.metadata`
3. Loads packages incrementally (30 per batch) to keep UI responsive
4. Displays total size of all packages combined

**Performance**: 1000+ packages typically load within 2-5 seconds.

#### Package Search
- **Debounced Input**: 200ms delay before filtering to prevent lag
- **Real-Time Results**: Matches package name anywhere in the string
- **Case-Insensitive**: Finds "Django" same as "django"
- **Preserves Full List**: Original unfiltered list retained for quick reset

#### Package Updates
- **Latest Version**: Installs the newest available version from PyPI
- **Specific Version**: Choose any previous version (e.g., "numpy==1.21.0")
- **Downgrade**: Safely downgrade to older releases
- **Verification**: Confirms successful installation before updating UI

#### Package Removal
1. **Confirmation Dialog**: Shows package name and current version
2. **Uninstall Process**: Uses `pip uninstall -y`
3. **Success Feedback**: Displays confirmation message
4. **Auto-Refresh**: Updates package list after removal

---

## Configuration

### Configuration File Location
- **Path**: `%LOCALAPPDATA%\PyLite_Manager\config.json`
- **Created**: Automatically on first run
- **Format**: JSON for easy editing

### Configuration Structure

```json
{
  "scan_folders": [
    "C:\\Users\\YourName\\Documents\\Projects",
    "C:\\Users\\YourName\\venvs",
    "D:\\CustomPythonEnv"
  ],
  "default_python_path": "C:\\Python312\\python.exe"
}
```

#### scan_folders
- **Type**: Array of directory paths
- **Purpose**: Directories to recursively search for virtual environments
- **Default**: Empty array (no scanning until configured)
- **Modification**: Use the UI to add/remove folders

#### default_python_path
- **Type**: String (path to python.exe)
- **Purpose**: Tracks which Python version was last set as default
- **Default**: Empty string
- **Modification**: Click "Set Default" on any Python version

### Editing Configuration Manually

You can edit `config.json` directly in any text editor:

```json
{
  "scan_folders": [
    "C:\\Users\\YourName\\PythonProjects\\venvs",
    "D:\\Workspace\\environments"
  ],
  "default_python_path": "C:\\Python312\\python.exe"
}
```

**Note**: Changes take effect after restarting the application.

---

## Architecture

### Project Structure

```
PyLite_Manager/
├── main.py                    # Application entry point
├── core/                      # Core business logic
│   ├── python_detector.py    # Detect Python installations
│   ├── venv_manager.py       # Virtual environment discovery & operations
│   ├── package_manager.py    # Package listing & management
│   └── windows_path.py       # Windows PATH registry manipulation
├── ui/                        # User interface components
│   ├── main_window.py        # Main application window & coordination
│   ├── venv_panel.py         # Left panel: environments
│   └── package_panel.py      # Right panel: packages
├── utils/                     # Shared utilities
│   ├── helpers.py            # Command execution, size calculation
│   └── config.py             # Configuration file management
└── README.md                  # This file
```

### Key Components

#### Core Module: `python_detector.py`
- **Function**: `detect_python_versions()` → List[PythonVersionInfo]
- **Method**: Calls `py -0p` to enumerate installed Python versions
- **Returns**: List of Python version info objects with executable paths

#### Core Module: `venv_manager.py`
- **Functions**:
  - `find_venvs(scan_roots)`: Recursively search for virtual environments
  - `create_venv(target_path, python_spec)`: Create new virtual environment
  - `delete_venv(venv_path)`: Remove virtual environment folder
  - `open_venv_terminal(venv_path)`: Open terminal with venv activated
  - `open_folder(venv_path)`: Open folder in File Explorer
  - `uninstall_python_installation(executable)`: Launch Python uninstaller
- **Detection**: Multi-strategy layout-based detection

#### Core Module: `package_manager.py`
- **Functions**:
  - `list_packages(python_executable)`: Get installed packages
  - `stream_package_sizes(python_executable)`: Yield package sizes incrementally
  - `upgrade_package(python_executable, package_name)`: Update package
  - `install_package(python_executable, package_spec)`: Install specific version
  - `uninstall_package(python_executable, package_name)`: Remove package
  - `get_package_version(python_executable, package_name)`: Query installed version

#### Core Module: `windows_path.py`
- **Functions**:
  - `get_user_path_entries()`: Read PATH from registry
  - `set_user_path_entries(entries)`: Write PATH to registry
  - `prioritize_python_on_user_path(executable)`: Move Python to PATH front
- **Integration**: Registry manipulation with broadcast notification

#### UI Module: `main_window.py`
- **Role**: Main application window and event coordinator
- **Responsibilities**:
  - Load/save configuration
  - Refresh Python versions and environments
  - Handle package operations (install, update, uninstall)
  - Create/delete virtual environments
  - Manage async background operations
  - Update UI status and progress

#### UI Module: `venv_panel.py`
- **Role**: Left pane environment display
- **Components**:
  - Python versions tree view with horizontal scrolling
  - Scan folders list with horizontal scrolling
  - Virtual environments tree view with search and horizontal scrolling
  - New Venv button
- **Interactions**: Callbacks for actions and selections

#### UI Module: `package_panel.py`
- **Role**: Right pane package display
- **Components**:
  - Package tree view with name, version, size columns
  - Search bar with debouncing
  - Refresh button
  - Context menu for actions
  - Progress indicator for package operations
- **Features**: Incremental loading, horizontal scrolling

### Data Flow

```
User Action (Click/Right-Click)
    ↓
UI Handler (venv_panel.py / package_panel.py)
    ↓
Main Window Callback (main_window.py)
    ↓
Core Operation (python_detector.py / venv_manager.py / package_manager.py)
    ↓
System Interaction (subprocess / file I/O / registry)
    ↓
Status Update & UI Refresh (main_window.py)
```

### Threading Model

- **Main Thread**: Tkinter event loop (GUI updates)
- **Worker Threads**: Background operations (pip, scanning)
- **Communication**: `after()` callback to marshal results back to main thread
- **Safety**: No direct UI modification from worker threads

### Performance Optimizations

- **Incremental Package Loading**: Loads 30 packages at a time to keep UI responsive
- **Debounced Search**: 200ms delay prevents lag during typing
- **Concurrent Operations**: Package discovery and size calculation run in parallel
- **Deferred Size Updates**: Package sizes load progressively in background
- **Smart Caching**: Venv list cached until manual refresh
- **Lazy Initialization**: Packages only loaded when environment selected

---

## Troubleshooting

### Python Version Not Detected

**Problem**: Your Python installation doesn't appear in the list.

**Causes**:
- Python is not registered with the Windows Python Launcher
- `py` command is not available in PATH

**Solutions**:
1. Verify `py` command works:
   ```bash
   py --version
   ```

2. If not found, add Python to PATH manually or reinstall Python with "Add to PATH" option

3. Restart PyLite Manager to refresh the detection

### Virtual Environment Not Found

**Problem**: Your venv folder isn't discovered even after adding the scan folder.

**Causes**:
- Scan folder doesn't exist or is empty
- Virtual environment structure is non-standard
- Symbolic links or permission issues

**Solutions**:
1. Click **Refresh** after adding a scan folder
2. Verify the environment folder exists and contains expected structure
3. Check file permissions to ensure read access
4. Try creating a new test venv with the app to verify detection works

### Package Size Shows "..." (Loading)

**Problem**: Package size calculation is slow.

**Causes**:
- Large number of packages or large files
- Disk I/O performance
- Antivirus interference

**Solutions**:
1. Wait for loading to complete (typically 10-30 seconds for 100+ packages)
2. Check disk performance and close other resource-heavy applications
3. Temporarily disable antivirus real-time scanning if extremely slow
4. Use faster SSD storage if possible

### Failed to Install/Update Package

**Problem**: Package installation fails with an error.

**Causes**:
- Package doesn't exist on PyPI
- Version specification is invalid
- Dependency conflicts
- Network connectivity issues

**Solutions**:
1. Verify package name on PyPI: https://pypi.org
2. Check version spelling and format (e.g., "package==1.2.3")
3. Try installing simpler packages first to test connectivity
4. Check internet connection and proxy settings
5. Review error message for specific dependency issues

### Failed to Set Default Python

**Problem**: Setting default Python returns an error.

**Causes**:
- Insufficient permissions to modify PATH registry
- Antivirus blocking registry access
- Invalid Python installation path

**Solutions**:
1. Run PyLite Manager as Administrator
2. Check Windows Defender or antivirus settings
3. Manually verify Python executable exists at the displayed path
4. Try using Command Prompt `setx PATH "..."` directly

### Application Won't Start

**Problem**: PyLite Manager crashes on startup.

**Causes**:
- Corrupted config file
- Missing Python dependencies
- Tkinter not installed

**Solutions**:
1. Delete `%LOCALAPPDATA%\PyLite_Manager\config.json` and restart
2. Verify tkinter is installed:
   ```bash
   python -m tkinter
   ```
3. If tkinter missing, reinstall Python with all optional features
4. Check console output for specific error messages

### Performance Issues

**Problem**: Application is slow or unresponsive.

**Optimization Tips**:
1. **Limit Scan Folders**: Add only directories containing venvs
2. **Reduce Refresh Frequency**: Avoid rapid refresh clicks
3. **Search Efficiently**: Use precise search terms to filter packages
4. **Close Other Apps**: Reduce system resource competition
5. **SSD Storage**: Ensure PyLite_Manager and Python are on fast storage

### Right-Click Context Menu Issues

**Problem**: Right-clicking doesn't show the context menu or opens packages unexpectedly.

**Solutions**:
1. For Python versions: Right-click opens "Open Folder" menu only
2. For virtual environments: Right-click opens "Open Folder" or "Delete" menu without loading packages
3. For packages: Right-click opens "Update", "Downgrade", or "Uninstall" menu

---

## Development Notes

### Dependencies

- **Python**: 3.9+
- **tkinter**: Included with Python
- **Standard Library**:
  - subprocess, json, pathlib, dataclasses
  - threading, tkinter, winreg, ctypes

### Code Style

- Type hints throughout for clarity
- Dataclasses for data objects (slots=True for efficiency)
- Async pattern using threads and callbacks
- Minimal external dependencies (zero pip requirements)
- Clean separation of concerns: core, ui, utils


### Future Enhancements

Potential improvements:
- Support for other package managers (conda, pipenv, poetry)
- Package statistics and usage tracking
- Automated environment backups
- Multi-environment package operations
- Linux and macOS support
- Requirements.txt import/export
- Virtual environment cloning

---

## Support

For issues, feature requests, or contributions, please:
1. Check the [Issues Page](https://github.com/[owner]/PyLite_Manager/issues)
2. Create a new issue with detailed description
3. For contributions, fork the repository and submit a pull request

---

**Last Updated**: April 2026  
**Version**: 1.0  
**Status**: Production Ready  
**Author**: Thanniru Sai Teja
