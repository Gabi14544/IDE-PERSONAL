"""
PyMint IDE - Native Linux PTY Terminal Panel
Integrated VT100 terminal engine powered by pyte.
Full support for Zsh / Oh My Zsh, zero local duplicate echo,
correct Backspace / line-editing handling, no VT100 keypad artifact characters (=, >),
and seamless external Linux Mint terminal launcher.
"""

import os
import pty
import re
import signal
import struct
import fcntl
import termios
import shutil
import pyte
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QPlainTextEdit,
    QPushButton,
    QLabel,
    QApplication,
)
from PyQt6.QtCore import Qt, QSocketNotifier, pyqtSignal, QProcess
from PyQt6.QtGui import (
    QColor,
    QFont,
    QTextCursor,
    QTextCharFormat,
    QKeyEvent,
    QSyntaxHighlighter,
)
from core.config import settings
from ui.themes import get_theme


OSC_REGEX = re.compile(rb"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
KEYPAD_REGEX = re.compile(rb"\x1b[=>]")


class TerminalScreen(pyte.HistoryScreen):
    """
    Subclass of pyte.HistoryScreen that maintains an efficient scrollback string history.
    Lines scrolling off the top of the screen are archived directly as strings.
    """

    def __init__(self, cols: int, lines: int, history: int = 1000):
        super().__init__(cols, lines, history=history)
        self.history_lines = []

    def index(self):
        top, bottom = self.margins or pyte.screens.Margins(0, self.lines - 1)
        if self.cursor.y == bottom:
            row = self.buffer[top]
            max_col = max(row.keys(), default=-1)
            line_str = "".join(row[c].data for c in range(max_col + 1)).rstrip() if max_col >= 0 else ""
            self.history_lines.append(line_str)
            if len(self.history_lines) > 2000:
                self.history_lines.pop(0)
        super().index()


class TerminalHighlighter(QSyntaxHighlighter):
    """Lightweight prompt highlighter for Oh My Zsh tokens (green arrow, git branch, status)."""

    def __init__(self, theme_dict: dict, parent=None):
        super().__init__(parent)
        self.theme = theme_dict
        self._update_rules()

    def update_theme(self, theme_dict: dict):
        self.theme = theme_dict
        self._update_rules()
        self.rehighlight()

    def _update_rules(self):
        self.rules = []
        th = self.theme

        # Green prompt arrow (➜)
        fmt_green = QTextCharFormat()
        fmt_green.setForeground(QColor(th.get("green", "#59A869")))
        fmt_green.setFontWeight(QFont.Weight.Bold)
        self.rules.append((re.compile(r"➜"), fmt_green))

        # Blue git repository & branch badge: git:(master)
        fmt_blue = QTextCharFormat()
        fmt_blue.setForeground(QColor(th.get("syntax_func", th.get("blue", "#3B82F6"))))
        self.rules.append((re.compile(r"git:\([^)]*\)"), fmt_blue))

        # Red dirty symbol (✗)
        fmt_red = QTextCharFormat()
        fmt_red.setForeground(QColor(th.get("red", "#E06C75")))
        fmt_red.setFontWeight(QFont.Weight.Bold)
        self.rules.append((re.compile(r"✗"), fmt_red))

        # Teal directory name in prompt
        fmt_teal = QTextCharFormat()
        fmt_teal.setForeground(QColor(th.get("teal", "#2AACB8")))
        self.rules.append((re.compile(r"(?:~|/)[a-zA-Z0-9_\-\./]+"), fmt_teal))

    def highlightBlock(self, text: str):
        for pattern, fmt in self.rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


class PTYTerminalWidget(QPlainTextEdit):
    """VT100 PTY Terminal session driven by pyte state engine."""

    def __init__(self, cwd: str = "", theme_dict: dict = None, parent=None):
        super().__init__(parent)
        self.cwd = cwd or os.getcwd()
        self.theme = theme_dict or get_theme(settings.get_theme())
        self.master_fd = None
        self.slave_fd = None
        self.pid = None
        self.notifier = None
        self._last_rendered_content = ""

        # pyte virtual terminal screen & stream
        self.screen = TerminalScreen(80, 24, history=1000)
        self.stream = pyte.ByteStream(self.screen)

        self._init_editor_ui()
        self._spawn_pty()

    def _init_editor_ui(self):
        font_family = settings.get_font_family()
        font_size = settings.get_font_size()
        font = QFont(font_family, font_size)
        font.setFixedPitch(True)
        self.setFont(font)

        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setMaximumBlockCount(3000)

        bg = self.theme.get("terminal_bg", "#1E1F22")
        fg = self.theme.get("terminal_fg", "#E4E4E7")
        sel = self.theme.get("editor_selection", "#2E436E")

        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {bg};
                color: {fg};
                selection-background-color: {sel};
                selection-color: {fg};
                border: none;
                font-family: monospace;
            }}
        """)

        self.highlighter = TerminalHighlighter(self.theme, self.document())

    def apply_theme(self, theme_dict: dict, font: QFont = None):
        """Applies theme colors and font dynamically."""
        self.theme = theme_dict
        if font:
            self.setFont(font)

        bg = self.theme.get("terminal_bg", "#1E1F22")
        fg = self.theme.get("terminal_fg", "#E4E4E7")
        sel = self.theme.get("editor_selection", "#2E436E")

        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {bg};
                color: {fg};
                selection-background-color: {sel};
                selection-color: {fg};
                border: none;
                font-family: monospace;
            }}
        """)
        self.highlighter.update_theme(theme_dict)

    def _spawn_pty(self):
        """Forks child process attached to pseudo-terminal running the user's shell."""
        self.master_fd, self.slave_fd = pty.openpty()

        # Initial default window size
        try:
            winsize = struct.pack("HHHH", 24, 80, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
        except Exception:
            pass

        # Environment configuration
        env = dict(os.environ)
        env["TERM"] = "xterm-256color"
        env["COLORTERM"] = "truecolor"
        env["PROMPT_EOL_MARK"] = ""  # Disables Zsh inverse % symbol
        env["LANG"] = os.environ.get("LANG", "en_US.UTF-8")

        # Automatically bind .venv if present
        venv_path = os.path.join(self.cwd, ".venv")
        if os.path.isdir(venv_path):
            env["VIRTUAL_ENV"] = venv_path
            env["PATH"] = f"{os.path.join(venv_path, 'bin')}:{env.get('PATH', '')}"

        # Ensure cargo/rust binaries are accessible
        cargo_bin = os.path.expanduser("~/.cargo/bin")
        if os.path.isdir(cargo_bin) and cargo_bin not in env.get("PATH", "").split(os.pathsep):
            env["PATH"] = f"{cargo_bin}:{env.get('PATH', '')}"

        shell = os.environ.get("SHELL", "/bin/bash")
        if not os.path.exists(shell):
            shell = "/bin/bash"

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

            os.execvpe(shell, [shell, "-i"], env)
        else:
            # Parent process
            os.close(self.slave_fd)
            self.slave_fd = None

            self.notifier = QSocketNotifier(self.master_fd, QSocketNotifier.Type.Read, self)
            self.notifier.activated.connect(self._read_from_pty)

    def _read_from_pty(self):
        """Reads output bytes from master PTY, cleans OSC/keypad noise, and feeds pyte."""
        if self.master_fd is None:
            return

        try:
            raw_bytes = os.read(self.master_fd, 8192)
            if not raw_bytes:
                return

            # Clean OSC window title sequences (\x1b]0;...\x07)
            data = OSC_REGEX.sub(b"", raw_bytes)
            # Clean VT100 keypad mode characters (\x1b= and \x1b>)
            data = KEYPAD_REGEX.sub(b"", data)

            self.stream.feed(data)
            self._render_screen()
        except OSError:
            if self.notifier:
                self.notifier.setEnabled(False)

    def _render_screen(self):
        """Renders pyte screen display buffer into QPlainTextEdit and updates cursor position."""
        visible = [line.rstrip() for line in self.screen.display]
        while visible and not visible[-1]:
            visible.pop()

        all_lines = self.screen.history_lines + visible
        content = "\n".join(all_lines)

        if content != self._last_rendered_content:
            sb = self.verticalScrollBar()
            was_at_bottom = (sb.value() >= sb.maximum() - 4)

            self.setPlainText(content)
            self._last_rendered_content = content

            # Move cursor to pyte screen cursor position
            block_idx = len(self.screen.history_lines) + self.screen.cursor.y
            doc = self.document()
            block = doc.findBlockByNumber(block_idx)
            if block.isValid():
                cur = QTextCursor(block)
                col = min(self.screen.cursor.x, max(0, block.length() - 1))
                cur.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, col)
                self.setTextCursor(cur)

            if was_at_bottom:
                self.ensureCursorVisible()

    def write_to_pty(self, text: str):
        """Sends command string directly to PTY master descriptor."""
        if self.master_fd is not None:
            try:
                os.write(self.master_fd, text.encode("utf-8"))
            except Exception:
                pass

    def send_sigint(self):
        """Sends Ctrl+C (SIGINT)."""
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
        """
        Translates keyboard events to PTY bytes.
        Never calls super().keyPressEvent(event) for typing keys to prevent duplicate local echo.
        """
        if self.master_fd is None:
            return

        key = event.key()
        modifiers = event.modifiers()
        ctrl = bool(modifiers & Qt.KeyboardModifier.ControlModifier)
        shift = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)

        # 1. Clipboard shortcuts
        if ctrl and shift and key == Qt.Key.Key_C:
            self.copy()
            event.accept()
            return

        if ctrl and shift and key == Qt.Key.Key_V:
            cb_text = QApplication.clipboard().text()
            if cb_text:
                try:
                    os.write(self.master_fd, cb_text.encode("utf-8"))
                except Exception:
                    pass
            event.accept()
            return

        # 2. Control key combinations
        if ctrl:
            if key == Qt.Key.Key_C:
                self.send_sigint()
                event.accept()
                return
            elif key == Qt.Key.Key_L:
                try:
                    os.write(self.master_fd, b"\x0c")
                except Exception:
                    pass
                event.accept()
                return
            elif key == Qt.Key.Key_D:
                try:
                    os.write(self.master_fd, b"\x04")
                except Exception:
                    pass
                event.accept()
                return
            elif key == Qt.Key.Key_Z:
                try:
                    os.write(self.master_fd, b"\x1a")
                except Exception:
                    pass
                event.accept()
                return
            elif key == Qt.Key.Key_A:
                try:
                    os.write(self.master_fd, b"\x01")
                except Exception:
                    pass
                event.accept()
                return
            elif key == Qt.Key.Key_E:
                try:
                    os.write(self.master_fd, b"\x05")
                except Exception:
                    pass
                event.accept()
                return
            elif key == Qt.Key.Key_U:
                try:
                    os.write(self.master_fd, b"\x15")
                except Exception:
                    pass
                event.accept()
                return
            elif key == Qt.Key.Key_K:
                try:
                    os.write(self.master_fd, b"\x0b")
                except Exception:
                    pass
                event.accept()
                return
            elif key == Qt.Key.Key_W:
                try:
                    os.write(self.master_fd, b"\x17")
                except Exception:
                    pass
                event.accept()
                return
            elif key == Qt.Key.Key_R:
                try:
                    os.write(self.master_fd, b"\x12")
                except Exception:
                    pass
                event.accept()
                return

        # 3. Special navigation & editing keys
        key_map = {
            Qt.Key.Key_Return: b"\r",
            Qt.Key.Key_Enter: b"\r",
            Qt.Key.Key_Backspace: b"\x7f",
            Qt.Key.Key_Delete: b"\x1b[3~",
            Qt.Key.Key_Tab: b"\t",
            Qt.Key.Key_Up: b"\x1b[A",
            Qt.Key.Key_Down: b"\x1b[B",
            Qt.Key.Key_Right: b"\x1b[C",
            Qt.Key.Key_Left: b"\x1b[D",
            Qt.Key.Key_Home: b"\x1b[H",
            Qt.Key.Key_End: b"\x1b[F",
            Qt.Key.Key_PageUp: b"\x1b[5~",
            Qt.Key.Key_PageDown: b"\x1b[6~",
            Qt.Key.Key_Escape: b"\x1b",
        }

        if key in key_map:
            try:
                os.write(self.master_fd, key_map[key])
            except Exception:
                pass
            event.accept()
            return

        # 4. Standard printable character input
        text = event.text()
        if text:
            try:
                os.write(self.master_fd, text.encode("utf-8"))
            except Exception:
                pass
            event.accept()
            return

    def resizeEvent(self, event):
        """Synchronizes pyte screen dimensions and kernel TIOCSWINSZ window rows/cols."""
        super().resizeEvent(event)
        if self.master_fd is None:
            return

        font_metrics = self.fontMetrics()
        char_w = max(1, font_metrics.horizontalAdvance("W"))
        char_h = max(1, font_metrics.height())

        cols = max(20, self.viewport().width() // char_w)
        lines = max(5, self.viewport().height() // char_h)

        if self.screen.columns != cols or self.screen.lines != lines:
            self.screen.resize(lines, cols)

        try:
            winsize = struct.pack("HHHH", lines, cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
        except Exception:
            pass

    def close(self):
        """Clean termination of PTY and child shell process."""
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
    """Multi-tabbed terminal panel with quick launches and Mint external terminal integration."""

    collapse_requested = pyqtSignal()

    def __init__(self, project_dir: str = "", theme_dict: dict = None, parent=None):
        super().__init__(parent)
        self.project_dir = project_dir or os.getcwd()
        self.theme = theme_dict or get_theme(settings.get_theme())

        self._init_ui()
        self.new_terminal_tab("Terminal 1")

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header toolbar inside Terminal island
        self.header = QWidget()
        self.header.setObjectName("islandHeader")
        h_layout = QHBoxLayout(self.header)
        h_layout.setContentsMargins(8, 4, 8, 4)
        h_layout.setSpacing(6)

        title = QLabel("TERMINAL")
        title.setObjectName("islandHeaderTitle")
        h_layout.addWidget(title)

        h_layout.addSpacing(6)

        # FastAPI button
        btn_fastapi = QPushButton("▶ FastAPI")
        btn_fastapi.setToolTip("uv run uvicorn main:app --reload")
        btn_fastapi.clicked.connect(self.run_fastapi)
        h_layout.addWidget(btn_fastapi)

        # Django button
        btn_django = QPushButton("▶ Django")
        btn_django.setToolTip("uv run python manage.py runserver")
        btn_django.clicked.connect(self.run_django)
        h_layout.addWidget(btn_django)

        # Stop button
        btn_stop = QPushButton("⏹ Stop")
        btn_stop.setToolTip("Send SIGINT (Ctrl+C) to current terminal")
        btn_stop.clicked.connect(self.stop_current_process)
        h_layout.addWidget(btn_stop)

        h_layout.addStretch()

        # Native Linux Mint Terminal button [↗ Terminal Nativa Mint]
        btn_native = QPushButton("↗ Terminal Nativa Mint")
        btn_native.setToolTip("Abrir en la terminal nativa del sistema (gnome-terminal)")
        btn_native.clicked.connect(self.open_native_terminal)
        h_layout.addWidget(btn_native)

        # New tab button [+]
        btn_new_tab = QPushButton("+")
        btn_new_tab.setObjectName("islandHeaderBtn")
        btn_new_tab.setToolTip("Nueva pestaña de terminal")
        btn_new_tab.setFixedSize(22, 22)
        btn_new_tab.clicked.connect(lambda: self.new_terminal_tab())
        h_layout.addWidget(btn_new_tab)

        # Collapse button [—]
        btn_collapse = QPushButton("—")
        btn_collapse.setObjectName("islandHeaderBtn")
        btn_collapse.setToolTip("Ocultar terminal (Ctrl+J)")
        btn_collapse.setFixedSize(22, 22)
        btn_collapse.clicked.connect(self.collapse_requested.emit)
        h_layout.addWidget(btn_collapse)

        layout.addWidget(self.header)

        # Tabs container
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        layout.addWidget(self.tabs)

    def set_project_dir(self, path: str):
        self.project_dir = path

    def new_terminal_tab(self, name: str = None) -> PTYTerminalWidget:
        """Spawns a new terminal tab in current project directory."""
        tab_name = name or f"Terminal {self.tabs.count() + 1}"
        term = PTYTerminalWidget(cwd=self.project_dir, theme_dict=self.theme, parent=self)
        idx = self.tabs.addTab(term, tab_name)
        self.tabs.setCurrentIndex(idx)
        term.setFocus()
        return term

    def current_terminal(self) -> PTYTerminalWidget:
        widget = self.tabs.currentWidget()
        return widget if isinstance(widget, PTYTerminalWidget) else None

    def close_tab(self, index: int):
        if self.tabs.count() <= 1:
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

    def send_command_to_terminal(self, cmd: str):
        """Sends a command to the active terminal tab, ensuring it runs interactively with enter."""
        term = self.current_terminal() or self.new_terminal_tab()
        term.setFocus()
        clean_cmd = cmd.rstrip("\r\n")
        term.write_to_pty(f"{clean_cmd}\r")

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

    def open_native_terminal(self):
        """Launches native Linux Mint terminal (gnome-terminal, x-terminal-emulator) in project directory."""
        target_dir = self.project_dir or os.getcwd()
        for term_bin in ["gnome-terminal", "x-terminal-emulator", "xfce4-terminal", "xterm"]:
            if shutil.which(term_bin):
                if term_bin in ("gnome-terminal", "xfce4-terminal"):
                    QProcess.startDetached(term_bin, [f"--working-directory={target_dir}"])
                else:
                    QProcess.startDetached(term_bin, [], target_dir)
                return

    def apply_theme(self, theme_dict: dict, font: QFont = None):
        """Updates theme for all terminal tabs."""
        self.theme = theme_dict
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, PTYTerminalWidget):
                widget.apply_theme(theme_dict, font)
