"""
PyMint IDE - Editor Tabs Manager
Handles multiple open files, tab switching, modification indicators (*),
saving, and lint/formatting integration with dynamic theme switching.
"""

import os
from PyQt6.QtWidgets import (
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QMessageBox,
    QLabel,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QIcon, QFont

from ui.code_editor import CodeEditor
from core.linter_runner import LinterRunner
from core.config import settings
from ui.themes import get_theme


class EditorTabs(QTabWidget):
    """Tabbed container for code editor instances."""

    file_opened = pyqtSignal(str)
    file_saved = pyqtSignal(str)
    active_editor_changed = pyqtSignal(object)  # CodeEditor or None
    status_message_requested = pyqtSignal(str)

    def __init__(self, lsp_worker=None, theme_dict: dict = None, parent=None):
        super().__init__(parent)
        self.lsp_worker = lsp_worker
        self.theme = theme_dict or get_theme(settings.get_theme())
        self.linter = LinterRunner(self)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setDocumentMode(True)

        self._modified_states = {}  # filepath -> bool
        self._editors = {}          # filepath -> CodeEditor

        self.tabCloseRequested.connect(self.close_tab)
        self.currentChanged.connect(self._on_current_tab_changed)

        self.linter.lint_completed.connect(self._on_lint_completed)
        self.linter.format_completed.connect(self._on_format_completed)

        self._apply_tab_style()

    def close_all(self):
        """Cleanly terminates linter before closing."""
        self.linter.stop_all()

    def _apply_tab_style(self):
        """Card-themed tab bar styling with rounded tab tops and clear active state."""
        th = self.theme
        card_bg = th["card_bg"]
        card_border = th["card_border"]
        header_bg = th["header_bg"]
        text = th["text"]
        text_muted = th["text_muted"]
        accent = th["accent"]
        surface = th["surface"]

        self.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background: {card_bg};
            }}
            QTabBar::tab {{
                background: {header_bg};
                color: {text_muted};
                padding: 6px 14px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                border: 1px solid {card_border};
                border-bottom: none;
                margin-right: 2px;
                font-size: 11px;
            }}
            QTabBar::tab:selected {{
                background: {card_bg};
                color: {accent};
                border-top: 2px solid {accent};
                font-weight: bold;
            }}
            QTabBar::tab:hover:!selected {{
                background: {surface};
                color: {text};
            }}
        """)

    def apply_theme(self, theme_dict: dict, font: QFont = None):
        """Propagates theme and font to all open editors and updates tab styling."""
        self.theme = theme_dict
        self._apply_tab_style()
        for editor in self._editors.values():
            editor.apply_theme(theme_dict, font)

    def open_file(self, filepath: str) -> CodeEditor:
        """Opens a file in a new tab or switches to it if already open."""
        filepath = os.path.abspath(filepath)

        # Check if already open
        if filepath in self._editors:
            editor = self._editors[filepath]
            index = self.indexOf(editor)
            if index != -1:
                self.setCurrentIndex(index)
                return editor

        # Read file contents safely
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception as e:
            QMessageBox.critical(self, "Error opening file", f"Could not read {filepath}:\n{e}")
            return None

        editor = CodeEditor(
            filepath=filepath,
            lsp_worker=self.lsp_worker,
            theme_dict=self.theme,
            parent=self,
        )
        editor.setText(content)
        editor.setModified(False)

        # Hook editor signals
        editor.save_requested.connect(lambda: self.save_file(filepath))
        editor.format_requested.connect(lambda: self.format_file(filepath))
        editor.modificationChanged.connect(lambda mod: self._on_modification_changed(filepath, mod))
        editor.status_message_requested.connect(self.status_message_requested.emit)

        tab_title = os.path.basename(filepath)
        index = self.addTab(editor, tab_title)
        self.setTabToolTip(index, filepath)
        self._editors[filepath] = editor
        self._modified_states[filepath] = False
        self.setCurrentIndex(index)

        settings.add_recent_file(filepath)
        self.file_opened.emit(filepath)

        # Run initial linter check if python or rust
        if filepath.endswith(".py") or filepath.endswith(".rs"):
            self.linter.check_file(filepath)

        return editor

    def save_file(self, filepath: str = None) -> bool:
        """Saves file to disk, clears dirty state, and runs linter check."""
        if not filepath:
            editor = self.current_editor()
            if not editor:
                return False
            filepath = editor.filepath

        if not filepath or filepath not in self._editors:
            return False

        editor = self._editors[filepath]
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(editor.text())
            editor.setModified(False)
            self._on_modification_changed(filepath, False)
            self.status_message_requested.emit(f"Saved: {os.path.basename(filepath)}")
            self.file_saved.emit(filepath)

            # Trigger linting
            if filepath.endswith(".py") or filepath.endswith(".rs"):
                self.linter.check_file(filepath)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error saving file", f"Could not save {filepath}:\n{e}")
            return False

    def save_all(self):
        """Saves all modified open files."""
        for filepath, modified in list(self._modified_states.items()):
            if modified:
                self.save_file(filepath)

    def format_file(self, filepath: str = None):
        """Asynchronously formats the file using Ruff (Python) or rustfmt (Rust)."""
        if not filepath:
            editor = self.current_editor()
            if not editor:
                return
            filepath = editor.filepath

        if not filepath or filepath not in self._editors:
            return

        editor = self._editors[filepath]
        if filepath.endswith(".py"):
            self.status_message_requested.emit(f"Formatting {os.path.basename(filepath)} with Ruff...")
            self.linter.format_code(filepath, editor.text())
        elif filepath.endswith(".rs"):
            self.status_message_requested.emit(f"Formatting {os.path.basename(filepath)} with rustfmt...")
            self.linter.format_code(filepath, editor.text())
        else:
            self.status_message_requested.emit("Format only supports Python and Rust files")

    def _on_format_completed(self, filepath: str, success: bool, output: str):
        """Replaces buffer with formatted code while preserving cursor position."""
        if not success:
            self.status_message_requested.emit(f"Format error: {output.strip()}")
            return

        if filepath in self._editors:
            editor = self._editors[filepath]
            line, col = editor.getCursorPosition()
            editor.setText(output)
            editor.setCursorPosition(line, col)
            self.status_message_requested.emit(f"Formatted: {os.path.basename(filepath)}")

    def _on_lint_completed(self, filepath: str, diagnostics: list):
        """Applies Ruff diagnostics markers to editor."""
        if filepath in self._editors:
            self._editors[filepath].set_diagnostics(diagnostics)

    def _on_modification_changed(self, filepath: str, modified: bool):
        """Appends asterisk (*) to tab text when file is modified."""
        self._modified_states[filepath] = modified
        if filepath in self._editors:
            editor = self._editors[filepath]
            index = self.indexOf(editor)
            if index != -1:
                title = os.path.basename(filepath)
                if modified:
                    title += " *"
                self.setTabText(index, title)

    def _on_current_tab_changed(self, index: int):
        editor = self.widget(index) if index != -1 else None
        self.active_editor_changed.emit(editor)
        if editor and isinstance(editor, CodeEditor):
            editor.setFocus()

    def current_editor(self) -> CodeEditor:
        widget = self.currentWidget()
        return widget if isinstance(widget, CodeEditor) else None

    def close_tab(self, index: int) -> bool:
        """Prompts to save if modified before closing."""
        widget = self.widget(index)
        if not isinstance(widget, CodeEditor):
            return True

        filepath = widget.filepath
        if self._modified_states.get(filepath, False):
            resp = QMessageBox.question(
                self,
                "Unsaved Changes",
                f"File '{os.path.basename(filepath)}' has unsaved changes.\nDo you want to save before closing?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if resp == QMessageBox.StandardButton.Save:
                if not self.save_file(filepath):
                    return False
            elif resp == QMessageBox.StandardButton.Cancel:
                return False

        self.removeTab(index)
        self._editors.pop(filepath, None)
        self._modified_states.pop(filepath, None)
        return True
