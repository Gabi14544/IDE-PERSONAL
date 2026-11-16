"""
PyMint IDE - Linter & Formatter Runner (Ruff in Rust)
Non-blocking asynchronous execution using Qt QProcess.
"""

import json
from PyQt6.QtCore import QObject, QProcess, pyqtSignal
from core.config import settings


class LinterRunner(QObject):
    """Asynchronously runs ruff check and ruff format on Python files."""
    lint_completed = pyqtSignal(str, list)       # filepath, diagnostics list
    format_completed = pyqtSignal(str, bool, str)  # filepath, success, formatted_code or error

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lint_processes = {}    # filepath -> QProcess
        self._format_processes = {}  # filepath -> QProcess

    def stop_all(self):
        """Terminates any running ruff check or format processes."""
        all_procs = list(self._lint_processes.values()) + list(self._format_processes.values())
        for proc in all_procs:
            try:
                proc.kill()
                proc.waitForFinished(50)
            except Exception:
                pass
        self._lint_processes.clear()
        self._format_processes.clear()

    def check_file(self, filepath: str):
        """Asynchronously checks a file using ruff check for Python or rustc for Rust."""
        if filepath.endswith(".py"):
            self._check_python(filepath)
        elif filepath.endswith(".rs"):
            self._check_rust(filepath)
        else:
            self.lint_completed.emit(filepath, [])

    def _check_python(self, filepath: str):
        """Runs ruff check on Python file."""
        ruff_bin = settings.get_ruff_path()

        if filepath in self._lint_processes:
            old_proc = self._lint_processes[filepath]
            if old_proc.state() == QProcess.ProcessState.Running:
                old_proc.kill()

        process = QProcess(self)
        self._lint_processes[filepath] = process

        def on_finished(exit_code, exit_status):
            try:
                raw_output = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace")
                self._lint_processes.pop(filepath, None)
                process.deleteLater()
            except RuntimeError:
                return

            diagnostics = []
            if raw_output.strip():
                try:
                    data = json.loads(raw_output)
                    if isinstance(data, list):
                        for item in data:
                            loc = item.get("location", {})
                            row = loc.get("row", 1) - 1  # 0-indexed for QScintilla
                            col = loc.get("column", 1)
                            diagnostics.append({
                                "line": max(0, row),
                                "col": col,
                                "code": item.get("code", "Ruff"),
                                "message": item.get("message", ""),
                                "severity": item.get("severity", "error"),
                            })
                except Exception:
                    pass

            self.lint_completed.emit(filepath, diagnostics)

        process.finished.connect(on_finished)
        process.start(ruff_bin, ["check", "--output-format=json", filepath])

    def _check_rust(self, filepath: str):
        """Runs rustc non-codegen metadata check for instant error feedback on Rust file."""
        rustc_bin = settings.get_rustc_path()

        if filepath in self._lint_processes:
            old_proc = self._lint_processes[filepath]
            if old_proc.state() == QProcess.ProcessState.Running:
                old_proc.kill()

        process = QProcess(self)
        self._lint_processes[filepath] = process

        def on_finished(exit_code, exit_status):
            try:
                raw_output = bytes(process.readAllStandardError()).decode("utf-8", errors="replace")
                self._lint_processes.pop(filepath, None)
                process.deleteLater()
            except RuntimeError:
                return

            diagnostics = []
            if raw_output.strip():
                for line in raw_output.splitlines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        if data.get("$message_type") == "diagnostic":
                            spans = data.get("spans", [])
                            primary = next((s for s in spans if s.get("is_primary")), spans[0] if spans else None)
                            if not primary:
                                continue
                            row = max(0, primary.get("line_start", 1) - 1)
                            col = primary.get("column_start", 1)
                            code_obj = data.get("code")
                            code_str = code_obj.get("code", "Rust") if isinstance(code_obj, dict) else "Rust"
                            diagnostics.append({
                                "line": row,
                                "col": col,
                                "code": code_str,
                                "message": data.get("message", ""),
                                "severity": "error" if data.get("level") == "error" else "warning",
                            })
                    except Exception:
                        pass

            self.lint_completed.emit(filepath, diagnostics)

        process.finished.connect(on_finished)
        # Fast non-blocking syntax check emitting only metadata without binary output
        process.start(rustc_bin, ["--error-format=json", "--emit=metadata", "-o", "/tmp/pymint_rust_check_meta", filepath])

    def format_code(self, filepath: str, code_content: str):
        """Asynchronously formats code via stdin using ruff format for Python or rustfmt for Rust."""
        if filepath.endswith(".rs"):
            self._format_rust(filepath, code_content)
        else:
            self._format_python(filepath, code_content)

    def _format_python(self, filepath: str, code_content: str):
        """Formats Python code with Ruff."""
        ruff_bin = settings.get_ruff_path()

        if filepath in self._format_processes:
            old_proc = self._format_processes[filepath]
            if old_proc.state() == QProcess.ProcessState.Running:
                old_proc.kill()

        process = QProcess(self)
        self._format_processes[filepath] = process

        def on_finished(exit_code, exit_status):
            stdout = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace")
            stderr = bytes(process.readAllStandardError()).decode("utf-8", errors="replace")
            self._format_processes.pop(filepath, None)
            process.deleteLater()

            if exit_code == 0:
                self.format_completed.emit(filepath, True, stdout)
            else:
                self.format_completed.emit(filepath, False, stderr or "Format failed")

        process.finished.connect(on_finished)
        process.start(ruff_bin, ["format", "-"])
        process.write(code_content.encode("utf-8"))
        process.closeWriteChannel()

    def _format_rust(self, filepath: str, code_content: str):
        """Formats Rust code with rustfmt."""
        rustfmt_bin = settings.get_rustfmt_path()

        if filepath in self._format_processes:
            old_proc = self._format_processes[filepath]
            if old_proc.state() == QProcess.ProcessState.Running:
                old_proc.kill()

        process = QProcess(self)
        self._format_processes[filepath] = process

        def on_finished(exit_code, exit_status):
            stdout = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace")
            stderr = bytes(process.readAllStandardError()).decode("utf-8", errors="replace")
            self._format_processes.pop(filepath, None)
            process.deleteLater()

            if exit_code == 0 and stdout.strip():
                self.format_completed.emit(filepath, True, stdout)
            else:
                self.format_completed.emit(filepath, False, stderr or "rustfmt failed")

        process.finished.connect(on_finished)
        process.start(rustfmt_bin, ["--emit", "stdout"])
        process.write(code_content.encode("utf-8"))
        process.closeWriteChannel()
