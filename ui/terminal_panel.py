"""Bounded PTY sessions with batched, incremental Qt rendering."""

from collections import deque
from dataclasses import dataclass
import errno
import fcntl
import os
import shlex
import shutil
import signal
import struct
import termios
import subprocess
import sys
from pathlib import Path

import pyte
from PyQt6.QtCore import Qt, QSocketNotifier, QTimer, pyqtSignal, QProcess
from PyQt6.QtGui import QColor, QFont, QTextCursor, QTextCharFormat, QSyntaxHighlighter
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QPlainTextEdit,
    QPushButton,
    QLabel,
    QApplication,
    QMenu,
)

from core.config import settings
from ui.themes import get_theme


@dataclass(frozen=True)
class TerminalRow:
    text: str
    # (UTF-16 offset, length, pyte character attributes)
    runs: tuple = ()


def snapshot(row, columns):
    """Freeze one changed row; history never retains mutable screen buffers."""
    last = min(columns - 1, max(row.keys(), default=-1))
    chars = [row[index] for index in range(last + 1)]
    while chars and chars[-1].data == " " and chars[-1].bg == "default":
        chars.pop()
    text = "".join(char.data for char in chars)
    runs = []
    offset = 0
    for char in chars:
        length = len(char.data.encode("utf-16-le")) // 2
        style = (
            char.fg,
            char.bg,
            char.bold,
            char.italics,
            char.underscore,
            char.reverse,
        )
        if length:
            if runs and runs[-1][2] == style:
                start, count, _ = runs[-1]
                runs[-1] = (start, count + length, style)
            else:
                runs.append((offset, length, style))
        offset += length
    return TerminalRow(text, tuple(runs))


class TerminalScreen(pyte.Screen):
    """A single bounded scrollback, instead of duplicating pyte's history."""

    def __init__(self, cols=80, lines=24, history=2000):
        self.history_rows = deque(maxlen=history)
        self.history_dropped = 0
        super().__init__(cols, lines)

    def index(self):
        top, bottom = self.margins or pyte.screens.Margins(0, self.lines - 1)
        if self.cursor.y == bottom and top == 0 and bottom == self.lines - 1:
            if len(self.history_rows) == self.history_rows.maxlen:
                self.history_dropped += 1
            self.history_rows.append(snapshot(self.buffer[top], self.columns))
        super().index()

    def erase_in_display(self, how=0, *args, **kwargs):
        if how == 3:
            self.history_dropped += len(self.history_rows)
            self.history_rows.clear()
        super().erase_in_display(how, *args, **kwargs)

    def reset(self):
        self.history_dropped += len(self.history_rows)
        self.history_rows.clear()
        super().reset()


class TerminalHighlighter(QSyntaxHighlighter):
    """Render the terminal's real SGR colors, rather than guessing from prompt text."""

    COLORS = {
        "black": "#454b59",
        "red": "#e27881",
        "green": "#a2c98d",
        "brown": "#e5bc8a",
        "blue": "#82aaff",
        "magenta": "#c3a6ff",
        "cyan": "#89cdd0",
        "white": "#dce1ea",
        "brightblack": "#7b8797",
        "brightred": "#ff9a9e",
        "brightgreen": "#b5dfa0",
        "brightbrown": "#f4d19e",
        "brightblue": "#a3bfff",
        "brightmagenta": "#d4beff",
        "brightcyan": "#a2e4e6",
        "brightwhite": "#ffffff",
    }

    def __init__(self, terminal):
        super().__init__(terminal.document())
        self.terminal = terminal
        self._formats = {}

    def color(self, value, fallback):
        if value == "default":
            return QColor(fallback)
        return QColor(self.COLORS.get(value, f"#{value}"))

    def highlightBlock(self, text):
        index = self.currentBlock().blockNumber()
        rows = self.terminal._rows
        if index >= len(rows):
            return
        for start, length, style in rows[index].runs:
            fmt = self._formats.get(style)
            if fmt is None:
                fg, bg, bold, italic, underline, reverse = style
                theme = self.terminal.theme
                foreground = self.color(fg, theme["terminal_fg"])
                background = self.color(bg, theme["terminal_bg"])
                if reverse:
                    foreground, background = background, foreground
                fmt = QTextCharFormat()
                fmt.setForeground(foreground)
                fmt.setBackground(background)
                fmt.setFontWeight(QFont.Weight.Bold if bold else QFont.Weight.Normal)
                fmt.setFontItalic(italic)
                fmt.setFontUnderline(underline)
                # Bound the cache even for programs emitting many true colors.
                if len(self._formats) >= 512:
                    self._formats.clear()
                self._formats[style] = fmt
            self.setFormat(start, length, fmt)


class PTYTerminalWidget(QPlainTextEdit):
    session_finished = pyqtSignal(int)

    def __init__(self, cwd="", theme_dict=None, parent=None, command=None):
        super().__init__(parent)
        self.cwd = cwd or os.getcwd()
        self.theme = theme_dict or get_theme(settings.get_theme())
        self.master_fd = None
        self.pid = None
        self._process = None
        self.notifier = None
        self._write_notifier = None
        self._pending_write = bytearray()
        self._rows = []
        self._history_dropped = 0
        self._visible_rows = {}
        self._render_count = 0
        self._closed = False
        self.command = command
        self.screen = TerminalScreen()
        self.stream = pyte.ByteStream(self.screen)
        self.screen.write_process_input = self.write_to_pty
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(33)
        self._render_timer.timeout.connect(self._render_screen)
        self._reap_timer = QTimer(self)
        self._reap_timer.setInterval(250)
        self._reap_timer.timeout.connect(self._check_child)
        self.setReadOnly(True)
        self.setUndoRedoEnabled(False)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.document().setDocumentMargin(8)
        self.highlighter = TerminalHighlighter(self)
        self.apply_theme(
            self.theme, QFont(settings.get_font_family(), settings.get_font_size())
        )
        self._spawn_pty()

    def apply_theme(self, theme_dict, font=None):
        self.theme = theme_dict
        if font:
            self.setFont(font)
        self.setStyleSheet(f"""
            QPlainTextEdit {{ background: {self.theme["terminal_bg"]}; color: {self.theme["terminal_fg"]};
                selection-background-color: {self.theme["editor_selection"]}; border: none; padding: 0; }}
        """)
        self.highlighter._formats.clear()
        self.highlighter.rehighlight()
        self._sync_size()

    def _spawn_pty(self):
        master, slave = pty_open()
        env = dict(os.environ)
        env.update(TERM="xterm-256color", COLORTERM="truecolor")
        venv = os.path.join(self.cwd, ".venv")
        if os.path.isdir(venv):
            env["VIRTUAL_ENV"] = venv
            env["PATH"] = f"{venv}/bin:{env.get('PATH', '')}"
        shell = os.environ.get("SHELL", "/bin/bash")
        if not os.path.isfile(shell):
            shell = "/bin/bash"
        argv = self.command or [shell, "-i"]
        helper = Path(__file__).resolve().parents[1] / "core" / "pty_process.py"
        try:
            fcntl.ioctl(
                slave,
                termios.TIOCSWINSZ,
                struct.pack("HHHH", self.screen.lines, self.screen.columns, 0, 0),
            )
            # No Python code runs after fork in the multithreaded Qt parent.
            self._process = subprocess.Popen(
                [sys.executable, "-I", "-S", str(helper), *argv],
                stdin=slave,
                stdout=slave,
                stderr=slave,
                cwd=self.cwd,
                env=env,
                start_new_session=True,
                close_fds=True,
            )
            self.pid = self._process.pid
        except OSError:
            os.close(master)
            raise
        finally:
            os.close(slave)
        self.master_fd = master
        os.set_blocking(master, False)
        self.notifier = QSocketNotifier(master, QSocketNotifier.Type.Read, self)
        self.notifier.activated.connect(self._read_from_pty)
        self._write_notifier = QSocketNotifier(master, QSocketNotifier.Type.Write, self)
        self._write_notifier.setEnabled(False)
        self._write_notifier.activated.connect(self._flush_write)
        self._sync_size()
        self._reap_timer.start()

    def _read_from_pty(self):
        if self.master_fd is None:
            return
        try:
            # Bound parser work per event so keyboard and paint events get a turn.
            data = os.read(self.master_fd, 16384)
        except BlockingIOError:
            return
        except OSError as error:
            if error.errno != errno.EIO:
                self.setToolTip(f"Error de terminal: {error}")
            data = b""
        if data:
            # ByteStream retains split UTF-8 and escape sequences across reads.
            self.stream.feed(data)
            if not self._render_timer.isActive():
                self._render_timer.start()
        else:
            self._disconnect_pty()
            self._render_screen()

    def _render_screen(self):
        self._render_timer.stop()
        for line in range(self.screen.lines):
            if line in self.screen.dirty or line not in self._visible_rows:
                self._visible_rows[line] = snapshot(
                    self.screen.buffer[line], self.screen.columns
                )
        self.screen.dirty.clear()
        visible = [self._visible_rows[line] for line in range(self.screen.lines)]
        while len(visible) > self.screen.cursor.y + 1 and not visible[-1].text:
            visible.pop()
        rows = list(self.screen.history_rows) + visible
        old = self._rows
        scrollbar = self.verticalScrollBar()
        follow = (
            scrollbar.value() >= scrollbar.maximum() - 2
            and not self.textCursor().hasSelection()
        )
        dropped = self.screen.history_dropped - self._history_dropped
        self._history_dropped = self.screen.history_dropped
        scroll_value = max(0, scrollbar.value() - dropped)
        selection = self.textCursor()
        self._rows = rows
        if dropped and old:
            count = min(dropped, len(old))
            cursor = QTextCursor(self.document())
            block = self.document().findBlockByNumber(count)
            if block.isValid():
                cursor.setPosition(block.position(), QTextCursor.MoveMode.KeepAnchor)
                cursor.removeSelectedText()
            else:
                self.document().clear()
            old = old[count:]
        prefix = 0
        while prefix < min(len(old), len(rows)) and old[prefix] == rows[prefix]:
            prefix += 1
        if prefix < max(len(old), len(rows)):
            # Replace only the changed suffix. Normal typing touches one block,
            # leaving scrollback, undo allocation and unchanged layout alone.
            cursor = QTextCursor(self.document())
            block = self.document().findBlockByNumber(prefix)
            if block.isValid():
                cursor.setPosition(block.position())
            else:
                cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.movePosition(
                QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor
            )
            replacement = "\n".join(row.text for row in rows[prefix:])
            if prefix >= len(old) and prefix > 0:
                replacement = "\n" + replacement
            cursor.insertText(replacement)
            self._render_count += 1
        if follow:
            block = self.document().findBlockByNumber(
                len(self.screen.history_rows) + self.screen.cursor.y
            )
            if block.isValid():
                cursor = QTextCursor(block)
                row = self.screen.buffer[self.screen.cursor.y]
                text = "".join(
                    row[col].data
                    for col in range(min(self.screen.cursor.x, self.screen.columns))
                )
                column = min(len(text.encode("utf-16-le")) // 2, block.length() - 1)
                cursor.setPosition(block.position() + column)
                self.setTextCursor(cursor)
            scrollbar.setValue(scrollbar.maximum())
        else:
            if selection.hasSelection():
                self.setTextCursor(selection)
            scrollbar.setValue(scroll_value)

    def write_to_pty(self, text):
        if self.master_fd is None:
            return
        self._pending_write.extend(
            text.encode("utf-8") if isinstance(text, str) else text
        )
        self._flush_write()

    def _flush_write(self):
        if self.master_fd is None:
            return
        try:
            count = (
                os.write(self.master_fd, self._pending_write)
                if self._pending_write
                else 0
            )
            del self._pending_write[:count]
        except BlockingIOError:
            pass
        except OSError:
            self._pending_write.clear()
        self._write_notifier.setEnabled(bool(self._pending_write))

    def paste(self):
        text = QApplication.clipboard().text()
        if text:
            if 2004 << 5 in self.screen.mode:
                text = "\x1b[200~" + text + "\x1b[201~"
            self.write_to_pty(text)

    def insertFromMimeData(self, source):
        self.write_to_pty(source.text())

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        copy = menu.addAction("Copiar", self.copy)
        copy.setEnabled(self.textCursor().hasSelection())
        menu.addAction("Pegar", self.paste)
        menu.exec(event.globalPos())

    def send_sigint(self):
        # The terminal driver targets the foreground job, including its children.
        self.write_to_pty(b"\x03")

    def keyPressEvent(self, event):
        key, modifiers = event.key(), event.modifiers()
        ctrl = bool(modifiers & Qt.KeyboardModifier.ControlModifier)
        shift = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
        alt = bool(modifiers & Qt.KeyboardModifier.AltModifier)
        if ctrl and shift and key in (Qt.Key.Key_C, Qt.Key.Key_V):
            self.copy() if key == Qt.Key.Key_C else self.paste()
        elif shift and key in (Qt.Key.Key_PageUp, Qt.Key.Key_PageDown):
            scrollbar = self.verticalScrollBar()
            direction = -1 if key == Qt.Key.Key_PageUp else 1
            scrollbar.setValue(scrollbar.value() + direction * scrollbar.pageStep())
        elif ctrl and Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            self.write_to_pty(bytes([key - Qt.Key.Key_A + 1]))
        else:
            keys = {
                Qt.Key.Key_Return: b"\r",
                Qt.Key.Key_Enter: b"\r",
                Qt.Key.Key_Backspace: b"\x7f",
                Qt.Key.Key_Delete: b"\x1b[3~",
                Qt.Key.Key_Tab: b"\t",
                Qt.Key.Key_Backtab: b"\x1b[Z",
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
            data = keys.get(key, event.text().encode("utf-8"))
            if alt and data:
                data = b"\x1b" + data
            self.write_to_pty(data)
        event.accept()

    def _sync_size(self):
        metrics = self.fontMetrics()
        cols = max(
            20, (self.viewport().width() - 16) // max(1, metrics.horizontalAdvance("M"))
        )
        lines = max(3, (self.viewport().height() - 16) // max(1, metrics.lineSpacing()))
        if (self.screen.lines, self.screen.columns) != (lines, cols):
            self.screen.resize(lines, cols)
            self._visible_rows.clear()
            self._render_timer.start()
        if self.master_fd is not None:
            try:
                fcntl.ioctl(
                    self.master_fd,
                    termios.TIOCSWINSZ,
                    struct.pack("HHHH", lines, cols, 0, 0),
                )
            except OSError:
                pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sync_size()

    def _check_child(self):
        if not self.pid:
            return
        code = self._process.poll()
        if code is not None:
            self.pid = None
            self._reap_timer.stop()
            self.session_finished.emit(code)

    def _disconnect_pty(self):
        for notifier in (self.notifier, self._write_notifier):
            if notifier:
                notifier.setEnabled(False)
                notifier.deleteLater()
        self.notifier = self._write_notifier = None
        if self.master_fd is not None:
            os.close(self.master_fd)
            self.master_fd = None
        self._pending_write.clear()

    def closeEvent(self, event):
        if not self._closed:
            self._closed = True
            self._render_timer.stop()
            groups = set()
            if self.master_fd is not None:
                try:
                    groups.add(os.tcgetpgrp(self.master_fd))
                except OSError:
                    pass
            if self.pid:
                groups.add(self.pid)
            for group in groups:
                if group > 0 and group != os.getpgrp():
                    try:
                        os.killpg(group, signal.SIGHUP)
                        os.killpg(group, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            self._disconnect_pty()
            self._check_child()
            # Reap asynchronously if the kernel has not delivered child exit yet.
        super().closeEvent(event)


def pty_open():
    import pty

    return pty.openpty()


class TerminalPanel(QWidget):
    collapse_requested = pyqtSignal()

    def __init__(self, project_dir="", theme_dict=None, parent=None):
        super().__init__(parent)
        self.project_dir = project_dir or os.getcwd()
        self.theme = theme_dict or get_theme(settings.get_theme())
        self._run_terminal = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = QWidget()
        header.setObjectName("islandHeader")
        bar = QHBoxLayout(header)
        bar.setContentsMargins(12, 3, 8, 3)
        title = QLabel("TERMINAL")
        title.setObjectName("islandHeaderTitle")
        bar.addWidget(title)
        self.lbl_run_status = QLabel("")
        self.lbl_run_status.setObjectName("mutedLabel")
        bar.addWidget(self.lbl_run_status)
        bar.addStretch()
        self.btn_stop = QPushButton("■")
        self.btn_stop.setToolTip("Interrumpir ejecución o terminal activa (Shift+F5)")
        self.btn_stop.clicked.connect(self.stop_current_process)
        bar.addWidget(self.btn_stop)
        for text, tooltip, callback in (
            ("+", "Nueva terminal", lambda: self.new_terminal_tab()),
            ("↗", "Abrir terminal del sistema", self.open_native_terminal),
            ("−", "Ocultar terminal (Ctrl+J)", self.collapse_requested.emit),
        ):
            button = QPushButton(text)
            button.setObjectName("islandHeaderBtn")
            button.setFixedSize(26, 24)
            button.setToolTip(tooltip)
            button.clicked.connect(callback)
            bar.addWidget(button)
        layout.addWidget(header)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        layout.addWidget(self.tabs)
        self.new_terminal_tab()

    def set_project_dir(self, path):
        # Existing sessions keep their working directory; new sessions use this project.
        self.project_dir = path

    def new_terminal_tab(self, name=None, cwd=None):
        term = PTYTerminalWidget(cwd or self.project_dir, self.theme, self)
        index = self.tabs.addTab(term, name or f"Terminal {self.tabs.count() + 1}")
        term.session_finished.connect(
            lambda code, widget=term: self._session_finished(widget, code)
        )
        self.tabs.setCurrentIndex(index)
        term.setFocus()
        return term

    def _session_finished(self, term, code):
        index = self.tabs.indexOf(term)
        if index >= 0:
            self.tabs.setTabText(
                index, f"{'Ejecución' if term.command else 'Terminal'} · {code}"
            )
        if term is self._run_terminal:
            self.lbl_run_status.setText(f"Finalizó · código {code}")

    def run_is_active(self):
        return self._run_terminal is not None and self._run_terminal.pid is not None

    def run_command(self, argv, cwd, name):
        if self.run_is_active():
            return False
        if self._run_terminal is not None:
            index = self.tabs.indexOf(self._run_terminal)
            self._run_terminal.close()
            self._run_terminal.deleteLater()
            if index >= 0:
                self.tabs.removeTab(index)
        term = PTYTerminalWidget(cwd, self.theme, self, command=argv)
        self._run_terminal = term
        index = self.tabs.addTab(term, name)
        self.tabs.setTabToolTip(index, shlex.join(argv))
        self.tabs.setCurrentIndex(index)
        term.session_finished.connect(lambda code: self._session_finished(term, code))
        self.lbl_run_status.setText("En ejecución")
        term.setFocus()
        return True

    def current_terminal(self):
        return self.tabs.currentWidget()

    def close_tab(self, index):
        term = self.tabs.widget(index)
        if term is None:
            return
        if term is self._run_terminal:
            self._run_terminal = None
            self.lbl_run_status.clear()
        term.close()
        self.tabs.removeTab(index)
        # Keep the object until waitpid has reaped its shell.
        if term.pid:
            term.session_finished.connect(lambda _: term.deleteLater())
        else:
            term.deleteLater()
        if not self.tabs.count():
            self.new_terminal_tab()

    def send_command_to_terminal(self, cmd):
        term = self.current_terminal()
        if term is None or term.command or term.pid is None:
            term = self.new_terminal_tab()
        term.setFocus()
        term.write_to_pty(cmd.rstrip("\r\n") + "\r")

    def stop_current_process(self):
        term = self._run_terminal if self.run_is_active() else self.current_terminal()
        if term:
            term.send_sigint()

    def open_native_terminal(self):
        for binary in (
            "gnome-terminal",
            "x-terminal-emulator",
            "xfce4-terminal",
            "xterm",
        ):
            if shutil.which(binary):
                args = (
                    [f"--working-directory={self.project_dir}"]
                    if binary in ("gnome-terminal", "xfce4-terminal")
                    else []
                )
                QProcess.startDetached(binary, args, self.project_dir)
                return

    def apply_theme(self, theme_dict, font=None):
        self.theme = theme_dict
        for index in range(self.tabs.count()):
            self.tabs.widget(index).apply_theme(theme_dict, font)
