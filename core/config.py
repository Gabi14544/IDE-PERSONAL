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

# Default theme palette (JetBrains Air Dark aligned with compatibility keys)
THEME = {
    "crust": "#111317",
    "mantle": "#18191C",
    "base": "#1E1F22",
    "surface0": "#2B2D30",
    "surface1": "#36383E",
    "surface2": "#4E5157",
    "overlay0": "#8C929D",
    "text": "#E4E4E7",
    "subtext0": "#A1A1AA",
    "subtext1": "#CBD5E1",
    "blue": "#3B82F6",
    "green": "#59A869",
    "red": "#E06C75",
    "peach": "#fab387",
    "yellow": "#E5B567",
    "mauve": "#cba6f7",
    "teal": "#2AACB8",
    "caret": "#FFFFFF",
    "selection": "#2E436E",
    "current_line": "#26282E",
    "line_number_bg": "#1E1F22",
    "line_number_fg": "#4E5157",
}

# Autocomplete & Performance settings
AUTOCOMPLETE_DEBOUNCE_MS = 350
RAM_CHECK_INTERVAL_MS = 3000
LOW_RAM_ALERT_MB = 450


class SettingsManager:
    """Manages persistent application settings using QSettings."""

    def __init__(self):
        self._settings = QSettings(APP_ORG, "PyMintIDE")

    def get_theme(self) -> str:
        return str(self._settings.value("theme", "Graphite"))

    def set_theme(self, theme_name: str):
        self._settings.setValue("theme", theme_name)

    def get_last_directory(self) -> str:
        last = self._settings.value("last_directory", "")
        if last and os.path.isdir(str(last)):
            return str(last)
        return str(Path.home())

    def set_last_directory(self, path: str):
        self._settings.setValue("last_directory", path)

    def get_font_family(self) -> str:
        return str(self._settings.value("font_family", "Monospace"))

    def set_font_family(self, family: str):
        self._settings.setValue("font_family", family)

    def get_font_size(self) -> int:
        return int(self._settings.value("font_size", 11))

    def set_font_size(self, size: int):
        self._settings.setValue("font_size", size)

    def get_tab_width(self) -> int:
        return int(self._settings.value("tab_width", 4))

    def get_venv_python(self, project_dir: str = "") -> str:
        """Finds .venv/bin/python inside the project directory or parent directories."""
        current = project_dir or self.get_last_directory()
        while current and current != os.path.dirname(current):
            venv_py = os.path.join(current, ".venv", "bin", "python")
            if os.path.isfile(venv_py) and os.access(venv_py, os.X_OK):
                return venv_py
            current = os.path.dirname(current)
        return ""

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

    def get_cargo_path(self) -> str:
        saved = self._settings.value("cargo_path", "")
        if saved and os.path.exists(str(saved)):
            return str(saved)
        found = shutil.which("cargo")
        if found:
            return found
        cargo_bin = os.path.expanduser("~/.cargo/bin/cargo")
        if os.path.exists(cargo_bin):
            return cargo_bin
        return "cargo"

    def get_rustc_path(self) -> str:
        saved = self._settings.value("rustc_path", "")
        if saved and os.path.exists(str(saved)):
            return str(saved)
        found = shutil.which("rustc")
        if found:
            return found
        rustc_bin = os.path.expanduser("~/.cargo/bin/rustc")
        if os.path.exists(rustc_bin):
            return rustc_bin
        return "rustc"

    def get_rustfmt_path(self) -> str:
        saved = self._settings.value("rustfmt_path", "")
        if saved and os.path.exists(str(saved)):
            return str(saved)
        found = shutil.which("rustfmt")
        if found:
            return found
        rustfmt_bin = os.path.expanduser("~/.cargo/bin/rustfmt")
        if os.path.exists(rustfmt_bin):
            return rustfmt_bin
        return "rustfmt"

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
