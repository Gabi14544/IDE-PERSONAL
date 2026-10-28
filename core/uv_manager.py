"""
PyMint IDE - UV Package & Environment Manager
Asynchronous integration with uv (Fast Astral package manager in Rust).
"""

import os
from PyQt6.QtCore import QObject, QProcess, pyqtSignal
from core.config import settings


class UVManager(QObject):
    """Manages virtual environments and backend dependencies via uv."""

    command_output = pyqtSignal(str)          # Streaming console output
    command_finished = pyqtSignal(str, bool)   # command_name, success
    project_env_changed = pyqtSignal()         # Emitted when .venv is created/modified

    # Preset backend dependency definitions
    PRESETS = {
        "FastAPI": ["fastapi", "uvicorn[standard]", "pydantic-settings"],
        "Django": ["django", "djangorestframework"],
        "PostgreSQL": ["psycopg[binary]", "sqlalchemy", "alembic"],
        "NoSQL": ["pymongo", "motor", "redis"],
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_process = None
        self.project_dir = os.getcwd()

    def set_project_dir(self, path: str):
        self.project_dir = path

    def has_venv(self) -> bool:
        venv_path = os.path.join(self.project_dir, ".venv")
        return os.path.isdir(venv_path)

    def has_pyproject(self) -> bool:
        return os.path.isfile(os.path.join(self.project_dir, "pyproject.toml"))

    def get_venv_python(self) -> str:
        py_path = os.path.join(self.project_dir, ".venv", "bin", "python")
        return py_path if os.path.isfile(py_path) else ""

    def run_uv_command(self, cmd_name: str, args: list):
        """Executes a uv command asynchronously in the project directory."""
        if self._current_process and self._current_process.state() == QProcess.ProcessState.Running:
            self.command_output.emit("[UV] A command is already running. Please wait...\n")
            return

        uv_bin = settings.get_uv_path()
        self.command_output.emit(f"\n[UV] Running: {uv_bin} {' '.join(args)}\n")

        self._current_process = QProcess(self)
        self._current_process.setWorkingDirectory(self.project_dir)

        def on_stdout():
            data = bytes(self._current_process.readAllStandardOutput()).decode("utf-8", errors="replace")
            self.command_output.emit(data)

        def on_stderr():
            data = bytes(self._current_process.readAllStandardError()).decode("utf-8", errors="replace")
            self.command_output.emit(data)

        def on_finished(exit_code, exit_status):
            success = (exit_code == 0)
            status_text = "COMPLETED" if success else f"FAILED (code {exit_code})"
            self.command_output.emit(f"[UV] {cmd_name} {status_text}\n")
            self._current_process.deleteLater()
            self._current_process = None
            if "venv" in cmd_name.lower() or "init" in cmd_name.lower() or "add" in cmd_name.lower():
                self.project_env_changed.emit()
            self.command_finished.emit(cmd_name, success)

        self._current_process.readyReadStandardOutput.connect(on_stdout)
        self._current_process.readyReadStandardError.connect(on_stderr)
        self._current_process.finished.connect(on_finished)

        self._current_process.start(uv_bin, args)

    def init_project(self):
        """Initializes pyproject.toml and .venv."""
        self.run_uv_command("init", ["init"])

    def create_venv(self):
        """Creates virtualenv using system-site-packages for low memory footprint."""
        # Use system Python 3.12 and system-site-packages
        self.run_uv_command("venv", ["venv", "--python", "/usr/bin/python3", "--system-site-packages"])

    def add_packages(self, packages: list):
        """Runs uv add <packages...>."""
        if not packages:
            return
        self.run_uv_command("add", ["add"] + packages)

    def remove_packages(self, packages: list):
        """Runs uv remove <packages...>."""
        if not packages:
            return
        self.run_uv_command("remove", ["remove"] + packages)

    def install_preset(self, preset_name: str):
        """Installs pre-configured stack packages."""
        pkgs = self.PRESETS.get(preset_name, [])
        if pkgs:
            self.add_packages(pkgs)
