"""
PyMint IDE - Jedi LSP Worker Thread
Handles code completions and signature help in background without blocking Qt UI thread.
"""

import sys
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition
import os

try:
    import jedi
    JEDI_AVAILABLE = True
except ImportError:
    JEDI_AVAILABLE = False


class CompletionRequest:
    def __init__(self, req_id: int, code: str, line: int, col: int, filepath: str, project_dir: str, python_path: str, prefix: str):
        self.req_id = req_id
        self.code = code
        self.line = line  # 1-indexed for Jedi
        self.col = col    # 0-indexed
        self.filepath = filepath
        self.project_dir = project_dir
        self.python_path = python_path
        self.prefix = prefix


class LSPWorker(QThread):
    """Background worker for Jedi completions and signatures."""
    completions_ready = pyqtSignal(int, str, list)  # req_id, prefix, list of string candidates
    signature_ready = pyqtSignal(int, str)          # req_id, signature description

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mutex = QMutex()
        self._cond = QWaitCondition()
        self._running = True
        self._pending_request = None
        self._last_project_dir = None
        self._last_python_path = None
        self._cached_project = None

    def request_completion(self, req_id: int, code: str, line: int, col: int, filepath: str, project_dir: str, python_path: str, prefix: str):
        """Submit a completion request (overwrites any pending unprocessed request)."""
        if not JEDI_AVAILABLE:
            return
        self._mutex.lock()
        self._pending_request = CompletionRequest(
            req_id, code, line, col, filepath, project_dir, python_path, prefix
        )
        self._cond.wakeOne()
        self._mutex.unlock()

    def stop(self):
        """Safely terminates the worker thread."""
        self._mutex.lock()
        self._running = False
        self._cond.wakeOne()
        self._mutex.unlock()
        self.wait(1000)

    def _get_project(self, project_dir: str, python_path: str):
        if (self._cached_project and 
            self._last_project_dir == project_dir and 
            self._last_python_path == python_path):
            return self._cached_project

        self._last_project_dir = project_dir
        self._last_python_path = python_path
        try:
            if python_path and os.path.exists(python_path):
                self._cached_project = jedi.Project(
                    path=project_dir or os.getcwd(),
                    environment_path=python_path,
                )
            else:
                self._cached_project = jedi.Project(path=project_dir or os.getcwd())
        except Exception:
            self._cached_project = None
        return self._cached_project

    def run(self):
        while True:
            self._mutex.lock()
            while self._running and self._pending_request is None:
                self._cond.wait(self._mutex)

            if not self._running:
                self._mutex.unlock()
                break

            req = self._pending_request
            self._pending_request = None
            self._mutex.unlock()

            if not req:
                continue

            try:
                proj = self._get_project(req.project_dir, req.python_path)
                script = jedi.Script(
                    code=req.code,
                    path=req.filepath or "untitled.py",
                    project=proj,
                )

                # Get completions
                completions = script.complete(req.line, req.col)
                # Keep top 60 completions to avoid memory/rendering overhead
                candidates = []
                seen = set()
                for c in completions:
                    name = c.name
                    if name not in seen:
                        seen.add(name)
                        candidates.append(name)
                    if len(candidates) >= 60:
                        break

                self.completions_ready.emit(req.req_id, req.prefix, candidates)

                # Check signatures
                try:
                    signatures = script.get_signatures(req.line, req.col)
                    if signatures:
                        sig = signatures[0]
                        sig_text = sig.to_string()
                        self.signature_ready.emit(req.req_id, sig_text)
                except Exception:
                    pass

            except Exception:
                # Never crash the worker on parse errors
                pass
