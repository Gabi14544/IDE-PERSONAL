"""Run with QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v."""

import fcntl
import os
from pathlib import Path
import struct
import sys
import tempfile
import termios
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_config = tempfile.TemporaryDirectory()
os.environ["XDG_CONFIG_HOME"] = _config.name

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QPushButton, QMessageBox

from core.execution import command_for_file
from core.lsp_worker import LSPWorker
from ui.main_window import MainWindow
from ui.terminal_panel import PTYTerminalWidget, TerminalScreen

app = QApplication.instance() or QApplication([])
app.setStyle("Fusion")


def wait_for(predicate, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        QTest.qWait(10)
    raise AssertionError("Timed out waiting for terminal")


class TerminalTests(unittest.TestCase):
    def setUp(self):
        self.widgets = []

    def tearDown(self):
        for widget in self.widgets:
            widget.close()
            wait_for(lambda: widget.pid is None)
            widget.deleteLater()
        app.processEvents()

    def terminal(self, code="import time; time.sleep(30)"):
        widget = PTYTerminalWidget(command=[sys.executable, "-u", "-c", code])
        self.widgets.append(widget)
        widget.resize(720, 200)
        widget.show()
        app.processEvents()
        return widget

    def test_split_utf8_and_escape_sequences_keep_colors(self):
        widget = self.terminal()
        for chunk in (
            b"\x1b]0;A split",
            b" title\x07\x1b=",
            b"\x1b[3",
            b"1mHola caf\xc3",
            b"\xa9\x1b[0m",
        ):
            widget.stream.feed(chunk)
        widget._render_screen()
        app.processEvents()
        self.assertEqual(widget.toPlainText(), "Hola café")
        colors = [
            item.format.foreground().color().name()
            for item in widget.document().firstBlock().layout().formats()
        ]
        self.assertIn("#e27881", colors)

    def test_typing_does_not_replace_scrollback(self):
        widget = self.terminal()
        widget.stream.feed(b"first\r\nsecond\r\ncurrent")
        widget._render_screen()
        changes = []
        widget.document().contentsChange.connect(
            lambda start, removed, added: changes.append(start)
        )
        widget.stream.feed(b"!")
        widget._render_screen()
        self.assertEqual(widget.toPlainText(), "first\nsecond\ncurrent!")
        self.assertTrue(changes)
        self.assertGreaterEqual(min(changes), len("first\nsecond\n"))

    def test_scrollback_eviction_keeps_document_in_sync(self):
        widget = self.terminal()
        widget.screen = TerminalScreen(40, 4, history=20)
        import pyte

        widget.stream = pyte.ByteStream(widget.screen)
        widget._visible_rows.clear()
        for index in range(100):
            widget.stream.feed(f"row {index}\r\n".encode())
            widget._render_screen()
        self.assertEqual(len(widget.screen.history_rows), 20)
        self.assertLessEqual(widget.document().blockCount(), 24)
        self.assertEqual(
            widget.toPlainText(), "\n".join(row.text for row in widget._rows)
        )
        self.assertIn("row 99", widget.toPlainText())
        widget.stream.feed(b"\x1b[3J\x1b[H\x1b[2J")
        widget._render_screen()
        self.assertEqual(widget.toPlainText(), "")
        self.assertEqual(len(widget.screen.history_rows), 0)

    def test_output_is_batched_and_ui_remains_responsive(self):
        widget = self.terminal(
            "for i in range(3000): print('record', i)\nprint('END_OF_OUTPUT')"
        )
        ticks = []
        from PyQt6.QtCore import QTimer

        timer = QTimer()
        timer.timeout.connect(lambda: ticks.append(time.monotonic()))
        timer.start(10)
        wait_for(lambda: widget.pid is None and widget.master_fd is None)
        timer.stop()
        self.assertIn("END_OF_OUTPUT", widget.toPlainText())
        self.assertLessEqual(len(widget.screen.history_rows), 2000)
        self.assertLess(widget._render_count, 100)
        self.assertTrue(ticks)

    def test_input_resize_interrupt_and_reaping(self):
        widget = self.terminal(
            "import time; print(input('name: '), flush=True); time.sleep(30)"
        )
        pid = widget.pid
        wait_for(lambda: "name:" in widget.toPlainText())
        widget.resize(600, 220)
        app.processEvents()
        rows, columns, _, _ = struct.unpack(
            "HHHH", fcntl.ioctl(widget.master_fd, termios.TIOCGWINSZ, b"\0" * 8)
        )
        self.assertEqual((rows, columns), (widget.screen.lines, widget.screen.columns))
        QTest.keyClicks(widget, "Ada")
        QTest.keyClick(widget, Qt.Key.Key_Return)
        wait_for(lambda: widget.toPlainText().count("Ada") >= 2)
        QTest.keyClick(widget, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
        wait_for(lambda: widget.pid is None and widget.master_fd is None)
        with self.assertRaises(ChildProcessError):
            os.waitpid(pid, os.WNOHANG)

    def test_large_input_is_not_dropped_on_nonblocking_write(self):
        widget = self.terminal(
            "import os, tty; tty.setraw(0); print('READY', flush=True); "
            "data = b''\nwhile len(data) < 100000: data += os.read(0, 100000 - len(data))\n"
            "print('RECEIVED', len(data), flush=True)"
        )
        wait_for(lambda: "READY" in widget.toPlainText())
        widget.write_to_pty("x" * 100000)
        wait_for(lambda: widget.pid is None and widget.master_fd is None)
        self.assertIn("RECEIVED 100000", widget.toPlainText())
        self.assertFalse(widget._pending_write)

    def test_scrolling_and_selection_survive_new_output(self):
        widget = self.terminal()
        widget.stream.feed(b"line\r\n" * 150)
        widget._render_screen()
        widget.verticalScrollBar().setValue(10)
        cursor = QTextCursor(widget.document())
        cursor.setPosition(5)
        cursor.setPosition(9, QTextCursor.MoveMode.KeepAnchor)
        widget.setTextCursor(cursor)
        selected = widget.textCursor().selectedText()
        scroll = widget.verticalScrollBar().value()
        widget.stream.feed(b"new output")
        widget._render_screen()
        self.assertEqual(widget.textCursor().selectedText(), selected)
        self.assertEqual(widget.verticalScrollBar().value(), scroll)


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.window = MainWindow(str(self.root))
        self.window.resize(1280, 680)
        self.window.show()
        app.processEvents()

    def tearDown(self):
        self.window.close()
        for index in range(self.window.terminal_panel.tabs.count()):
            term = self.window.terminal_panel.tabs.widget(index)
            wait_for(lambda: term.pid is None)
        self.window.deleteLater()
        app.processEvents()
        self.directory.cleanup()

    def test_small_screen_single_run_button_and_preferences(self):
        window = self.window
        self.assertEqual(window.editor_stack.currentIndex(), 0)
        buttons = [button.text() for button in window.findChildren(QPushButton)]
        self.assertFalse(
            any(
                "FastAPI" in text or "Django" in text or "Cargo" in text
                for text in buttons
            )
        )
        self.assertEqual(sum("Ejecutar" in text for text in buttons), 1)
        for width, height in ((1280, 680), (960, 600), (640, 400)):
            window.resize(width, height)
            app.processEvents()
            self.assertLessEqual(window.width(), width)
            self.assertLessEqual(window.height(), height)
        self.assertFalse(window.service_guard._check_processes)
        self.assertFalse(window.git_manager._active_processes)

    def test_run_saves_and_handles_hostile_filename_without_touching_shell(self):
        path = self.root / "code '$ weird.py"
        path.write_text("print('OLD')\n")
        editor = self.window.editor_tabs.open_file(str(path))
        editor.setText("print('RUN_SUCCESS')\n")
        shell = self.window.terminal_panel.current_terminal()
        self.window.activateWindow()
        editor.setFocus()
        app.processEvents()
        QTest.keyClick(editor, Qt.Key.Key_F5)
        runner = self.window.terminal_panel.current_terminal()
        self.assertIsNot(runner, shell)
        wait_for(lambda: runner.pid is None and runner.master_fd is None)
        self.assertIn("RUN_SUCCESS", runner.toPlainText())
        self.assertEqual(path.read_text(), "print('RUN_SUCCESS')\n")
        self.assertIsNotNone(shell.pid)
        self.window.run_active_file()
        second = self.window.terminal_panel.current_terminal()
        wait_for(lambda: second.pid is None and second.master_fd is None)
        self.assertEqual(self.window.terminal_panel.tabs.count(), 2)

    def test_active_run_is_not_started_twice(self):
        path = self.root / "wait.py"
        path.write_text("import time; time.sleep(30)\n")
        self.window.editor_tabs.open_file(str(path))
        self.window.run_active_file()
        runner = self.window.terminal_panel.current_terminal()
        self.window.run_active_file()
        self.assertIs(self.window.terminal_panel.current_terminal(), runner)
        self.assertEqual(self.window.terminal_panel.tabs.count(), 2)
        self.window.terminal_panel.stop_current_process()

    def test_failed_save_cancels_run(self):
        path = self.root / "code.py"
        path.write_text("print('hello')\n")
        self.window.editor_tabs.open_file(str(path))
        with patch.object(self.window.editor_tabs, "save_file", return_value=False):
            self.window.run_active_file()
        self.assertIsNone(self.window.terminal_panel._run_terminal)

    def test_close_can_be_cancelled_without_losing_changes(self):
        path = self.root / "unsaved.py"
        path.write_text("value = 1\n")
        editor = self.window.editor_tabs.open_file(str(path))
        editor.setText("value = 2\n")
        with patch.object(
            QMessageBox, "question", return_value=QMessageBox.StandardButton.Cancel
        ):
            self.window.close()
        self.assertTrue(self.window.isVisible())
        self.assertTrue(editor.isModified())
        self.assertEqual(path.read_text(), "value = 1\n")
        with patch.object(
            QMessageBox, "question", return_value=QMessageBox.StandardButton.Save
        ):
            self.assertTrue(self.window.editor_tabs.confirm_close())
        self.assertEqual(path.read_text(), "value = 2\n")

    def test_venv_command_is_absolute_unbuffered_and_not_a_shell(self):
        path = self.root / "folder" / 'a "quoted".py'
        path.parent.mkdir()
        path.touch()
        python = self.root / ".venv" / "bin" / "python"
        python.parent.mkdir(parents=True)
        python.symlink_to(sys.executable)
        argv, cwd = command_for_file(str(path), str(self.root))
        self.assertEqual(argv, [str(python), "-u", str(path)])
        self.assertEqual(cwd, str(self.root))

    def test_cursor_connections_do_not_accumulate(self):
        editors = []
        for name in ("first.py", "second.py"):
            path = self.root / name
            path.write_text("value = 1\n")
            editors.append(self.window.editor_tabs.open_file(str(path)))
        for _ in range(10):
            self.window.editor_tabs.setCurrentWidget(editors[0])
            self.window.editor_tabs.setCurrentWidget(editors[1])
        editors[0].cursor_info_changed.emit(88, 88)
        self.assertNotIn("88", self.window.lbl_cursor_pos.text())
        editors[1].cursor_info_changed.emit(7, 9)
        self.assertEqual(self.window.lbl_cursor_pos.text(), "Lín 7, Col 9")


class CompletionTests(unittest.TestCase):
    def test_worker_starts_on_demand_and_completes(self):
        worker = LSPWorker()
        self.assertFalse(worker.isRunning())
        results = []
        worker.completions_ready.connect(
            lambda request, prefix, items: results.append((request, items))
        )
        with tempfile.TemporaryDirectory() as root:
            worker.request_completion(
                123,
                "import os\nos.pa",
                2,
                5,
                str(Path(root) / "example.py"),
                root,
                sys.executable,
                "pa",
            )
            try:
                wait_for(lambda: bool(results))
                self.assertEqual(results[0][0], 123)
                self.assertIn("path", results[0][1])
            finally:
                worker.stop()
                wait_for(lambda: not worker.isRunning())


if __name__ == "__main__":
    unittest.main()
