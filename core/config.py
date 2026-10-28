"""
PyMint IDE - Core Configuration and Settings Management
Optimized for low-spec hardware (Intel Celeron / 4GB RAM)
"""

import os
import shutil
from pathlib import Path
from PyQt6.QtCore import QSettings

APP_NAME = "PyMint IDE"
APP_ORG = "PyMint"
APP_VERSION = "0.1.0"

# Files and directories ignored by file tree, search, and indexing
IGNORED_DIRS = {
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".git",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "postgres_data",
    "dist",
    "build",
    ".idea",
    ".vscode",
    ".cache",
    ".eggs",
}

IGNORED_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".so",
    ".dll",
    ".dylib",
    ".o",
    ".a",
    ".obj",
    ".iso",
    ".bin",
    ".sqlite3-journal",
}

# Dark theme palette (Catppuccin Mocha inspired for low eye strain)
THEME = {
    "crust": "#11111b",
    "mantle": "#181825",
    "base": "#1e1e2e",
    "surface0": "#313244",
    "surface1": "#45475a",
    "surface2": "#585b70",
    "overlay0": "#6c7086",
    "text": "#cdd6f4",
    "subtext0": "#a6adc8",
    "subtext1": "#bac2de",
    "blue": "#89b4fa",
    "green": "#a6e3a1",
    "red": "#f38ba8",
    "peach": "#fab387",
    "yellow": "#f9e2af",
    "mauve": "#cba6f7",
    "teal": "#94e2d5",
    "caret": "#f5e0dc",
    "selection": "#45475a",
    "current_line": "#24273a",
    "line_number_bg": "#181825",
    "line_number_fg": "#6c7086",
}

# Autocomplete & Performance settings
AUTOCOMPLETE_DEBOUNCE_MS = 350
RAM_CHECK_INTERVAL_MS = 3000
LOW_RAM_ALERT_MB = 450


class SettingsManager:
    """Manages persistent application settings using QSettings."""

    def __init__(self):
        self._settings = QSettings(APP_ORG, "PyMintIDE")

    def get_last_directory(self) -> str:
        last = self._settings.value("last_directory", "")
        if last and os.path.isdir(str(last)):
            return str(last)
        return str(Path.home())

    def set_last_directory(self, path: str):
        self._settings.setValue("last_directory", path)

    def get_font_family(self) -> str:
        return str(self._settings.value("font_family", "Monospace"))

    def get_font_size(self) -> int:
        return int(self._settings.value("font_size", 10))

    def get_tab_width(self) -> int:
        return int(self._settings.value("tab_width", 4))

    def get_uv_path(self) -> str:
        saved = self._settings.value("uv_path", "")
        if saved and os.path.exists(str(saved)):
            return str(saved)
        # Search PATH and common homebrew/local paths
        found = shutil.which("uv")
        if found:
            return found
        local_uv = os.path.expanduser("~/.local/bin/uv")
        if os.path.exists(local_uv):
            return local_uv
        cargo_uv = os.path.expanduser("~/.cargo/bin/uv")
        if os.path.exists(cargo_uv):
            return cargo_uv
        return "uv"

    def get_ruff_path(self) -> str:
        saved = self._settings.value("ruff_path", "")
        if saved and os.path.exists(str(saved)):
            return str(saved)
        found = shutil.which("ruff")
        if found:
            return found
        local_ruff = os.path.expanduser("~/.local/bin/ruff")
        if os.path.exists(local_ruff):
            return local_ruff
        return "ruff"

    def get_git_path(self) -> str:
        saved = self._settings.value("git_path", "")
        if saved and os.path.exists(str(saved)):
            return str(saved)
        found = shutil.which("git")
        return found or "git"

    def get_recent_files(self) -> list:
        return self._settings.value("recent_files", []) or []

    def add_recent_file(self, filepath: str):
        files = self.get_recent_files()
        if filepath in files:
            files.remove(filepath)
        files.insert(0, filepath)
        self._settings.setValue("recent_files", files[:15])

    def get_window_geometry(self):
        return self._settings.value("window_geometry", None)

    def set_window_geometry(self, geo):
        if geo:
            self._settings.setValue("window_geometry", geo)

    def get_window_state(self):
        return self._settings.value("window_state", None)

    def set_window_state(self, state):
        if state:
            self._settings.setValue("window_state", state)


# Global singleton instance
settings = SettingsManager()
