"""
PyMint IDE - Git & GitHub Version Control Manager
Fully asynchronous git client using Qt QProcess.
"""

import os
from PyQt6.QtCore import QObject, QProcess, pyqtSignal
from core.config import settings


class GitManager(QObject):
    """Asynchronously coordinates Git CLI commands."""

    status_updated = pyqtSignal(list, list)          # staged_files, unstaged_files
    branches_updated = pyqtSignal(str, list)         # current_branch, list_of_branches
    log_graph_updated = pyqtSignal(str)              # ascii git graph text
    diff_ready = pyqtSignal(str, str)                # filename, diff text
    command_output = pyqtSignal(str)                 # log/output string
    command_finished = pyqtSignal(str, bool, str)    # cmd_name, success, message

    def __init__(self, repo_dir: str = "", parent=None):
        super().__init__(parent)
        self.repo_dir = repo_dir or os.getcwd()
        self._active_processes = set()

    def set_repo_dir(self, path: str):
        self.repo_dir = path

    def is_repo(self) -> bool:
        git_dir = os.path.join(self.repo_dir, ".git")
        return os.path.exists(git_dir)

    def stop_all(self):
        """Terminates any background git processes."""
        for proc in list(self._active_processes):
            try:
                proc.kill()
                proc.waitForFinished(50)
            except Exception:
                pass
        self._active_processes.clear()

    def _run_git_async(self, cmd_name: str, args: list, callback=None):
        """Runs a git command asynchronously using QProcess."""
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

            success = (exit_code == 0)
            if callback:
                try:
                    callback(success, stdout, stderr)
                except Exception:
                    pass
            self.command_finished.emit(cmd_name, success, stdout if success else stderr)

        proc.finished.connect(on_finished)
        proc.start(git_bin, args)

    def refresh_status(self):
        """Fetches status --porcelain and parses staged/unstaged files."""
        if not self.is_repo():
            self.status_updated.emit([], [])
            return

        def parse(success, stdout, stderr):
            if not success:
                return
            staged = []
            unstaged = []
            for line in stdout.splitlines():
                if len(line) < 4:
                    continue
                x = line[0]
                y = line[1]
                filename = line[3:].strip()
                # If quoted path (spaces), strip quotes
                if filename.startswith('"') and filename.endswith('"'):
                    filename = filename[1:-1]

                # Staged changes (X in 'MADRC')
                if x in "MADRC":
                    staged.append({"file": filename, "status": x})

                # Unstaged / Untracked (Y in 'MD' or '??')
                if y in "MD":
                    unstaged.append({"file": filename, "status": y})
                elif x == "?" and y == "?":
                    unstaged.append({"file": filename, "status": "?"})

            self.status_updated.emit(staged, unstaged)

        self._run_git_async("status", ["status", "--porcelain"], parse)

    def refresh_branches(self):
        """Gets current branch and all branches."""
        if not self.is_repo():
            return

        def parse(success, stdout, stderr):
            if not success:
                return
            branches = []
            current = "master"
            for line in stdout.splitlines():
                clean = line.strip()
                if clean.startswith("* "):
                    current = clean[2:].strip()
                    branches.append(current)
                elif clean:
                    branches.append(clean)
            self.branches_updated.emit(current, branches)

        self._run_git_async("branch", ["branch", "--no-color"], parse)

    def refresh_log_graph(self):
        """Fetches ASCII git graph of commits."""
        if not self.is_repo():
            return

        def parse(success, stdout, stderr):
            if success:
                self.log_graph_updated.emit(stdout)

        self._run_git_async(
            "log",
            ["log", "--graph", "--oneline", "--decorate", "--all", "-n", "40"],
            parse,
        )

    def stage_file(self, filename: str):
        def on_done(success, out, err):
            self.refresh_status()
        self._run_git_async("stage", ["add", filename], on_done)

    def unstage_file(self, filename: str):
        def on_done(success, out, err):
            self.refresh_status()
        self._run_git_async("unstage", ["restore", "--staged", filename], on_done)

    def stage_all(self):
        def on_done(success, out, err):
            self.refresh_status()
        self._run_git_async("stage_all", ["add", "-A"], on_done)

    def unstage_all(self):
        def on_done(success, out, err):
            self.refresh_status()
        self._run_git_async("unstage_all", ["restore", "--staged", "."], on_done)

    def commit(self, message: str):
        if not message.strip():
            return
        def on_done(success, out, err):
            self.refresh_status()
            self.refresh_log_graph()
        self._run_git_async("commit", ["commit", "-m", message], on_done)

    def checkout_branch(self, branch_name: str):
        def on_done(success, out, err):
            self.refresh_branches()
            self.refresh_status()
            self.refresh_log_graph()
        self._run_git_async("checkout", ["checkout", branch_name], on_done)

    def create_branch(self, new_branch_name: str):
        def on_done(success, out, err):
            self.refresh_branches()
            self.refresh_status()
            self.refresh_log_graph()
        self._run_git_async("create_branch", ["checkout", "-b", new_branch_name], on_done)

    def fetch(self):
        def on_done(success, out, err):
            self.refresh_branches()
            self.refresh_log_graph()
        self._run_git_async("fetch", ["fetch", "--all"], on_done)

    def pull(self):
        def on_done(success, out, err):
            self.refresh_status()
            self.refresh_branches()
            self.refresh_log_graph()
        self._run_git_async("pull", ["pull"], on_done)

    def push(self):
        def on_done(success, out, err):
            self.refresh_branches()
            self.refresh_log_graph()
        self._run_git_async("push", ["push"], on_done)

    def get_diff(self, filename: str, staged: bool = False):
        """Asynchronously gets diff for file."""
        args = ["diff"]
        if staged:
            args.append("--staged")
        args.append(filename)

        def parse(success, stdout, stderr):
            self.diff_ready.emit(filename, stdout if success else stderr)

        self._run_git_async("diff", args, parse)

    def clone(self, repo_url: str, target_dir: str):
        """Clones a remote GitHub repository."""
        self._run_git_async("clone", ["clone", repo_url, target_dir])
