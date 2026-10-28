"""
PyMint IDE - Native Linux PTY Terminal Panel
High-performance, non-blocking multi-tab terminal using os.openpty,
QSocketNotifier, ANSI color handling, and backend quick-launch controls.
"""

import os
import pty
import re
import signal
import struct
import fcntl
import termios
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QPlainTextEdit,
    QPushButton,
    QLabel,
    QTabBar,
)
from PyQt6.QtCore import Qt, QSocketNotifier, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QTextCursor,
    QTextCharFormat,
    QKeyEvent,
)

from core.config import THEME, settings

# ANSI 16-color palette mapped to Catppuccin Mocha
ANSI_COLORS = {
    30: THEME["surface1"],    # Black
    31: THEME["red"],         # Red
    32: THEME["green"],       # Green
    33: THEME["yellow"],      # Yellow
    34: THEME["blue"],        # Blue
    35: THEME["mauve"],       # Magenta
    36: THEME["teal"],        # Cyan
    37: THEME["text"],        # White
    90: THEME["overlay0"],    # Bright Black / Gray
    91: "#eba0ac",            # Bright Red
    92: "#94e2d5",            # Bright Green
    93: "#f9e2af",            # Bright Yellow
    94: "#89dceb",            # Bright Blue
    95: "#f5c2e7",            # Bright Magenta
    96: "#74c7ec",            # Bright Cyan
    97: "#ffffff",            # Bright White
}

ANSI_REGEX = re.compile(r"\x1b\[([0-9;]*)m")


class PTYTerminalWidget(QPlainTextEdit):
    """Single PTY terminal session embedded inside QPlainTextEdit."""

    title_changed = pyqtSignal(str)

    def __init__(self, cwd: str = "", parent=None):
        super().__init__(parent)
        self.cwd = cwd or os.getcwd()
        self.master_fd = None
        self.slave_fd = None
        self.pid = None
        self.notifier = None

        self._init_editor_ui()
        self._spawn_pty()

    def _init_editor_ui(self):
        font_family = settings.get_font_family()
        font_size = settings.get_font_size()
        font = QFont(font_family, font_size)
        font.setFixedPitch(True)
        self.setFont(font)

        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setMaximumBlockCount(2500)  # Memory safeguard on low-spec hardware

        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {THEME['mantle']};
                color: {THEME['text']};
                selection-background-color: {THEME['selection']};
                selection-color: {THEME['text']};
                border: none;
                font-family: monospace;
            }}
        """)

        # Default text format
        self.default_format = QTextCharFormat()
        self.default_format.setForeground(QColor(THEME["text"]))
        self.current_format = QTextCharFormat(self.default_format)

    def _spawn_pty(self):
        """Fork child process attached to pseudo-terminal."""
        self.master_fd, self.slave_fd = pty.openpty()

        # Set default window size (24x80)
        try:
            winsize = struct.pack("HHHH", 24, 100, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
        except Exception:
            pass

        # Prepare environment with .venv auto-activation if present
        env = dict(os.environ)
        env["TERM"] = "xterm-256color"
        env["LANG"] = "en_US.UTF-8"
        venv_path = os.path.join(self.cwd, ".venv")
        if os.path.isdir(venv_path):
            env["VIRTUAL_ENV"] = venv_path
            env["PATH"] = f"{os.path.join(venv_path, 'bin')}:{env.get('PATH', '')}"

        self.pid = os.fork()
        if self.pid == 0:
            # Child process
            os.close(self.master_fd)
            os.setsid()
            try:
                fcntl.ioctl(self.slave_fd, termios.TIOCSCTTY, 0)
            except Exception:
                pass

            os.dup2(self.slave_fd, 0)
            os.dup2(self.slave_fd, 1)
            os.dup2(self.slave_fd, 2)
            os.close(self.slave_fd)

            try:
                os.chdir(self.cwd)
            except Exception:
                pass

            os.execvpe("/bin/bash", ["/bin/bash", "-i"], env)
        else:
            # Parent process
            os.close(self.slave_fd)
            self.slave_fd = None

            # Socket notifier for asynchronous non-blocking read
            self.notifier = QSocketNotifier(self.master_fd, QSocketNotifier.Type.Read, self)
            self.notifier.activated.connect(self._read_from_pty)

    def _read_from_pty(self):
        """Called when PTY has data available."""
        if self.master_fd is None:
            return

        try:
            raw_bytes = os.read(self.master_fd, 4096)
            if not raw_bytes:
                return
            text = raw_bytes.decode("utf-8", errors="replace")
            self._append_ansi_text(text)
        except OSError:
            # PTY closed
            if self.notifier:
                self.notifier.setEnabled(False)

    def _append_ansi_text(self, text: str):
        """Parses basic ANSI color codes and prints to console."""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        parts = ANSI_REGEX.split(text)
        for i, part in enumerate(parts):
            if i % 2 == 1:
                # ANSI control codes
                codes = [int(c) for c in part.split(";") if c.isdigit()]
                if not codes or 0 in codes:
                    self.current_format = QTextCharFormat(self.default_format)
                for code in codes:
                    if code in ANSI_COLORS:
                        self.current_format.setForeground(QColor(ANSI_COLORS[code]))
                    elif code == 1:
                        self.current_format.setFontWeight(QFont.Weight.Bold)
            else:
                # Text content
                # Clean unsupported control sequences
                clean_part = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", part)
                # Handle carriage returns
                clean_part = clean_part.replace("\r\n", "\n").replace("\r", "\n")
                if clean_part:
                    cursor.insertText(clean_part, self.current_format)

        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def write_to_pty(self, text: str):
        """Sends string command to PTY."""
        if self.master_fd is not None:
            try:
                os.write(self.master_fd, text.encode("utf-8"))
            except Exception:
                pass

    def send_sigint(self):
        """Sends Ctrl+C (SIGINT) to interrupt running command/server."""
        if self.pid:
            try:
                os.kill(self.pid, signal.SIGINT)
            except Exception:
                pass
        if self.master_fd is not None:
            try:
                os.write(self.master_fd, b"\x03")
            except Exception:
                pass

    def keyPressEvent(self, event: QKeyEvent):
        """Translates keyboard events to PTY bytes."""
        if self.master_fd is None:
            super().keyPressEvent(event)
            return

        key = event.key()
        modifiers = event.modifiers()
        ctrl = bool(modifiers & Qt.KeyboardModifier.ControlModifier)

        # Control combinations
        if ctrl:
            if key == Qt.Key.Key_C:
                self.send_sigint()
                event.accept()
                return
            elif key == Qt.Key.Key_D:
                os.write(self.master_fd, b"\x04")
                event.accept()
                return
            elif key == Qt.Key.Key_L:
                self.clear()
                os.write(self.master_fd, b"\x0c")
                event.accept()
                return
            elif key == Qt.Key.Key_Z:
                os.write(self.master_fd, b"\x1a")
                event.accept()
                return

        # Special navigation keys
        key_map = {
            Qt.Key.Key_Return: b"\r",
            Qt.Key.Key_Enter: b"\r",
            Qt.Key.Key_Backspace: b"\x7f",
            Qt.Key.Key_Tab: b"\t",
            Qt.Key.Key_Up: b"\x1b[A",
            Qt.Key.Key_Down: b"\x1b[B",
            Qt.Key.Key_Right: b"\x1b[C",
            Qt.Key.Key_Left: b"\x1b[D",
            Qt.Key.Key_Home: b"\x1b[H",
            Qt.Key.Key_End: b"\x1b[F",
            Qt.Key.Key_PageUp: b"\x1b[5~",
            Qt.Key.Key_PageDown: b"\x1b[6~",
            Qt.Key.Key_Delete: b"\x1b[3~",
        }

        if key in key_map:
            os.write(self.master_fd, key_map[key])
            event.accept()
            return

        text = event.text()
        if text:
            os.write(self.master_fd, text.encode("utf-8"))
            event.accept()
            return

        super().keyPressEvent(event)

    def resizeEvent(self, event):
        """Update PTY window rows and columns dynamically."""
        super().resizeEvent(event)
        if self.master_fd is None:
            return

        font_metrics = self.fontMetrics()
        char_width = max(1, font_metrics.horizontalAdvance("W"))
        char_height = max(1, font_metrics.height())

        cols = max(20, self.viewport().width() // char_width)
        rows = max(5, self.viewport().height() // char_height)

        try:
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
        except Exception:
            pass

    def close(self):
        """Cleanup PTY file descriptors and kill child process."""
        if self.notifier:
            self.notifier.setEnabled(False)
            self.notifier = None

        if self.pid:
            try:
                os.kill(self.pid, signal.SIGTERM)
            except Exception:
                pass
            self.pid = None

        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except Exception:
                pass
            self.master_fd = None

        super().close()


class TerminalPanel(QWidget):
    """Multi-tabbed terminal panel with Backend Quick-Launch buttons."""

    def __init__(self, project_dir: str = "", parent=None):
        super().__init__(parent)
        self.project_dir = project_dir or os.getcwd()

        self._init_ui()
        self.new_terminal_tab("Terminal 1")

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header toolbar with Backend Quick Launch buttons
        toolbar = QWidget()
        toolbar.setStyleSheet(f"background-color: {THEME['crust']}; border-bottom: 1px solid {THEME['surface0']};")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(8, 4, 8, 4)
        tb_layout.setSpacing(6)

        title = QLabel("TERMINAL")
        title.setStyleSheet(f"color: {THEME['subtext1']}; font-weight: bold; font-size: 11px;")
        tb_layout.addWidget(title)

        tb_layout.addSpacing(10)

        # Quick Launch: FastAPI
        btn_fastapi = QPushButton("▶ Run FastAPI")
        btn_fastapi.setToolTip("uv run uvicorn main:app --reload")
        btn_fastapi.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['surface0']};
                color: {THEME['teal']};
                border: 1px solid {THEME['surface1']};
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {THEME['surface1']};
            }}
        """)
        btn_fastapi.clicked.connect(self.run_fastapi)
        tb_layout.addWidget(btn_fastapi)

        # Quick Launch: Django
        btn_django = QPushButton("▶ Run Django")
        btn_django.setToolTip("uv run python manage.py runserver")
        btn_django.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['surface0']};
                color: {THEME['green']};
                border: 1px solid {THEME['surface1']};
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {THEME['surface1']};
            }}
        """)
        btn_django.clicked.connect(self.run_django)
        tb_layout.addWidget(btn_django)

        # Quick Action: Stop Server (SIGINT)
        btn_stop = QPushButton("⏹ Stop Server")
        btn_stop.setToolTip("Send SIGINT (Ctrl+C) to current terminal")
        btn_stop.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['surface0']};
                color: {THEME['red']};
                border: 1px solid {THEME['surface1']};
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {THEME['surface1']};
            }}
        """)
        btn_stop.clicked.connect(self.stop_current_process)
        tb_layout.addWidget(btn_stop)

        tb_layout.addStretch()

        # New Tab (+)
        btn_new_tab = QPushButton("+")
        btn_new_tab.setToolTip("New Terminal Tab")
        btn_new_tab.setFixedSize(24, 22)
        btn_new_tab.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['surface0']};
                color: {THEME['text']};
                border: none;
                border-radius: 3px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {THEME['surface1']};
            }}
        """)
        btn_new_tab.clicked.connect(lambda: self.new_terminal_tab())
        tb_layout.addWidget(btn_new_tab)

        layout.addWidget(toolbar)

        # Tab widget for terminals
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background: {THEME['mantle']};
            }}
            QTabBar::tab {{
                background: {THEME['crust']};
                color: {THEME['subtext0']};
                padding: 4px 10px;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
                border: 1px solid {THEME['surface0']};
                margin-right: 2px;
                font-size: 11px;
            }}
            QTabBar::tab:selected {{
                background: {THEME['mantle']};
                color: {THEME['text']};
                border-bottom: 2px solid {THEME['blue']};
            }}
        """)
        layout.addWidget(self.tabs)

    def set_project_dir(self, path: str):
        self.project_dir = path

    def new_terminal_tab(self, name: str = None) -> PTYTerminalWidget:
        """Spawns a new terminal tab."""
        tab_name = name or f"Terminal {self.tabs.count() + 1}"
        term = PTYTerminalWidget(cwd=self.project_dir, parent=self)
        idx = self.tabs.addTab(term, tab_name)
        self.tabs.setCurrentIndex(idx)
        term.setFocus()
        return term

    def current_terminal(self) -> PTYTerminalWidget:
        widget = self.tabs.currentWidget()
        return widget if isinstance(widget, PTYTerminalWidget) else None

    def close_tab(self, index: int):
        if self.tabs.count() <= 1:
            # Don't close last tab; respawn clean terminal instead
            term = self.tabs.widget(index)
            if isinstance(term, PTYTerminalWidget):
                term.close()
            self.tabs.removeTab(index)
            self.new_terminal_tab("Terminal 1")
            return

        term = self.tabs.widget(index)
        if isinstance(term, PTYTerminalWidget):
            term.close()
        self.tabs.removeTab(index)

    def run_fastapi(self):
        term = self.current_terminal() or self.new_terminal_tab("FastAPI")
        term.write_to_pty("uv run uvicorn main:app --reload\n")

    def run_django(self):
        term = self.current_terminal() or self.new_terminal_tab("Django")
        term.write_to_pty("uv run python manage.py runserver\n")

    def stop_current_process(self):
        term = self.current_terminal()
        if term:
            term.send_sigint()
