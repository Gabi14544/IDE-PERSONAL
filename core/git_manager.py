"""
PyMint IDE - Git Manager (Minimalist Version)
Focuses strictly on branch discovery and recent commit history.
All active modifications (add, commit, push, pull) are performed via integrated terminal.
"""

import os
from PyQt6.QtCore import QObject, QProcess, pyqtSignal
from core.config import settings


class GitManager(QObject):
    """Coordinates Git branch querying and commit history logging."""

    branches_updated = pyqtSignal(str, list)         # current_branch, list_of_all_branches
    log_graph_updated = pyqtSignal(str)              # formatted git log text
    status_updated = pyqtSignal(list, list)          # backwards compatibility

    def __init__(self, repo_dir: str = "", parent=None):
        super().__init__(parent)
        self.repo_dir = ""
        self.current_branch = "master"
        self._active_processes = set()
        self.set_repo_dir(repo_dir or os.getcwd())

    def set_repo_dir(self, path: str):
        """Resolves the canonical repository root using git rev-parse --show-toplevel."""
        target = os.path.abspath(path) if path else os.getcwd()
        self.repo_dir = target

        # Walking parent markers avoids spawning and synchronously waiting for Git
        # on the UI thread at startup, and supports linked worktrees (.git files).
        while True:
            if os.path.exists(os.path.join(target, ".git")):
                self.repo_dir = target
                break
            parent = os.path.dirname(target)
            if parent == target:
                break
            target = parent

    def is_repo(self) -> bool:
        """Checks if current directory is inside a Git repository."""
        return os.path.exists(os.path.join(self.repo_dir, ".git"))

    def stop_all(self):
        """Terminates active background git processes."""
        for proc in list(self._active_processes):
            try:
                proc.kill()
                proc.waitForFinished(50)
            except Exception:
                pass
        self._active_processes.clear()

    def _run_git_async(self, args: list, callback=None):
        """Runs git command asynchronously using QProcess."""
        if not self.is_repo():
            return

        git_bin = settings.get_git_path()
        proc = QProcess(self)
        proc.setWorkingDirectory(self.repo_dir)
        self._active_processes.add(proc)

        def on_finished(exit_code, exit_status):
            self._active_processes.discard(proc)
            try:
                stdout = bytes(proc.readAllStandardOutput()).decode("utf-8", errors="replace")
                stderr = bytes(proc.readAllStandardError()).decode("utf-8", errors="replace")
                proc.deleteLater()
            except RuntimeError:
                return

            if callback:
                try:
                    callback(exit_code == 0, stdout, stderr)
                except Exception:
                    pass

        proc.finished.connect(on_finished)
        proc.start(git_bin, args)

    def refresh_branches(self):
        """Fetches all local and remote branches (git branch -a)."""
        if not self.is_repo():
            self.branches_updated.emit("", [])
            return

        def parse(success, stdout, stderr):
            if not success:
                return
            branches = []
            current = ""
            for line in stdout.splitlines():
                raw = line.strip()
                if not raw:
                    continue
                if raw.startswith("* "):
                    branch_name = raw[2:].strip()
                    current = branch_name
                    branches.append(f"* {branch_name}")
                else:
                    branches.append(raw)

            if current:
                self.current_branch = current
            self.branches_updated.emit(self.current_branch, branches)

        self._run_git_async(["branch", "-a", "--no-color"], parse)

    def refresh_log_graph(self):
        """Fetches the last 40 commits formatted cleanly."""
        if not self.is_repo():
            self.log_graph_updated.emit("No Git repository found in this folder.")
            return

        def parse(success, stdout, stderr):
            if success and stdout.strip():
                self.log_graph_updated.emit(stdout.strip())
            elif success:
                self.log_graph_updated.emit("No commits yet in this repository.")
            else:
                self.log_graph_updated.emit(f"Error fetching git log: {stderr.strip()}")

        self._run_git_async(
            ["log", "--graph", "--pretty=format:%h - %s (%cr) <%an>", "--abbrev-commit", "-n", "40"],
            parse,
        )

    def checkout_branch(self, branch_name: str):
        """Checks out selected branch."""
        clean_name = branch_name.replace("* ", "").strip()
        if clean_name.startswith("remotes/origin/"):
            clean_name = clean_name.replace("remotes/origin/", "").strip()

        def on_done(success, stdout, stderr):
            self.refresh_branches()
            self.refresh_log_graph()

        self._run_git_async(["checkout", clean_name], on_done)

    def refresh_status(self):
        """Compatibility method for editor file save hooks."""
        self.refresh_branches()
        self.refresh_log_graph()
