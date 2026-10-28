"""
PyMint IDE - Code Editor Component
Powered by QsciScintilla, customized with Catppuccin Mocha theme,
debounced Jedi autocompletion, Ruff margin markers, and multi-language lexers.
"""

import os
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QKeyEvent
from PyQt6.Qsci import (
    QsciScintilla,
    QsciLexerPython,
    QsciLexerSQL,
    QsciLexerJSON,
    QsciLexerYAML,
    QsciLexerBash,
    QsciLexerMarkdown,
)

from core.config import THEME, settings, AUTOCOMPLETE_DEBOUNCE_MS


class CodeEditor(QsciScintilla):
    """Native code editor with high performance and low memory consumption."""

    save_requested = pyqtSignal()
    format_requested = pyqtSignal()
    cursor_info_changed = pyqtSignal(int, int)  # line, col
    status_message_requested = pyqtSignal(str)

    LIST_ID_AUTOCOMPLETE = 1

    def __init__(self, filepath: str = "", lsp_worker=None, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.lsp_worker = lsp_worker
        self._current_req_id = 0
        self._diagnostics = {}  # line (0-indexed) -> list of diagnostic dicts

        # Debounce timer for autocomplete to protect Celeron CPU
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(AUTOCOMPLETE_DEBOUNCE_MS)
        self._debounce_timer.timeout.connect(self._trigger_completion)

        self._init_editor_settings()
        self._init_margins()
        self._init_lexer()
        self._connect_signals()

    def _init_editor_settings(self):
        """Configure editor behavior and dark theme colors."""
        font_family = settings.get_font_family()
        font_size = settings.get_font_size()
        font = QFont(font_family, font_size)
        font.setFixedPitch(True)
        self.setFont(font)

        # Tabulation & Indentation
        tab_width = settings.get_tab_width()
        self.setTabWidth(tab_width)
        self.setIndentationsUseTabs(False)
        self.setAutoIndent(True)
        self.setIndentationGuides(True)
        self.setBackspaceUnindents(True)
        self.setTabIndents(True)

        # UTF-8 Encoding
        self.setUtf8(True)
        self.setEolMode(QsciScintilla.EolMode.EolUnix)

        # Caret & Current Line
        self.setCaretForegroundColor(QColor(THEME["caret"]))
        self.setCaretWidth(2)
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(QColor(THEME["current_line"]))

        # Selection Colors
        self.setSelectionBackgroundColor(QColor(THEME["selection"]))
        self.setSelectionForegroundColor(QColor(THEME["text"]))

        # Base Paper/Color
        self.setPaper(QColor(THEME["base"]))
        self.setColor(QColor(THEME["text"]))

        # Autocompletion UI settings
        self.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsNone)  # Controlled via Jedi
        self.setAutoCompletionCaseSensitivity(False)
        self.setAutoCompletionReplaceWord(True)

        # Matched Braces
        self.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)
        self.setMatchedBraceBackgroundColor(QColor(THEME["surface1"]))
        self.setMatchedBraceForegroundColor(QColor(THEME["yellow"]))
        self.setUnmatchedBraceForegroundColor(QColor(THEME["red"]))

    def _init_margins(self):
        """Setup line numbers, lint diagnostic markers, and folding margin."""
        # Margin 0: Line Numbers
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginWidth(0, "0000_")
        self.setMarginsBackgroundColor(QColor(THEME["line_number_bg"]))
        self.setMarginsForegroundColor(QColor(THEME["line_number_fg"]))

        # Margin 1: Lint / Diagnostics markers
        self.setMarginType(1, QsciScintilla.MarginType.SymbolMargin)
        self.setMarginWidth(1, 14)
        self.setMarginSensitivity(1, True)
        self.error_marker_id = self.markerDefine(QsciScintilla.MarkerSymbol.Circle)
        self.setMarkerBackgroundColor(QColor(THEME["red"]), self.error_marker_id)
        self.setMarkerForegroundColor(QColor(THEME["crust"]), self.error_marker_id)

        self.warning_marker_id = self.markerDefine(QsciScintilla.MarkerSymbol.RightArrow)
        self.setMarkerBackgroundColor(QColor(THEME["yellow"]), self.warning_marker_id)
        self.setMarkerForegroundColor(QColor(THEME["crust"]), self.warning_marker_id)

        # Margin 2: Code Folding
        self.setFolding(QsciScintilla.FoldStyle.BoxedTreeFoldStyle, 2)
        self.setFoldMarginColors(QColor(THEME["mantle"]), QColor(THEME["mantle"]))

    def _init_lexer(self):
        """Assign native QsciLexer based on file extension."""
        if not self.filepath:
            return

        ext = os.path.splitext(self.filepath)[1].lower()
        basename = os.path.basename(self.filepath).lower()

        font_family = settings.get_font_family()
        font_size = settings.get_font_size()
        font = QFont(font_family, font_size)

        lexer = None
        if ext == ".py":
            lexer = QsciLexerPython(self)
        elif ext in (".sql", ".pgsql"):
            lexer = QsciLexerSQL(self)
        elif ext == ".json":
            lexer = QsciLexerJSON(self)
        elif ext in (".yaml", ".yml"):
            lexer = QsciLexerYAML(self)
        elif ext in (".sh", ".bash", ".zsh", ".env") or basename in ("dockerfile", "entrypoint.sh"):
            lexer = QsciLexerBash(self)
        elif ext in (".md", ".markdown"):
            lexer = QsciLexerMarkdown(self)

        if lexer:
            lexer.setDefaultFont(font)
            lexer.setFont(font)
            lexer.setDefaultPaper(QColor(THEME["base"]))
            lexer.setDefaultColor(QColor(THEME["text"]))
            lexer.setPaper(QColor(THEME["base"]))
            lexer.setColor(QColor(THEME["text"]))

            # Apply palette styles to common lexer styles
            self._style_lexer(lexer, ext)
            self.setLexer(lexer)

    def _style_lexer(self, lexer, ext: str):
        """Apply Catppuccin Mocha colors to lexer tokens."""
        # Generic color overrides across lexer token indices
        base_color = QColor(THEME["text"])
        comment_color = QColor(THEME["overlay0"])
        string_color = QColor(THEME["green"])
        keyword_color = QColor(THEME["mauve"])
        func_color = QColor(THEME["blue"])
        number_color = QColor(THEME["peach"])
        op_color = QColor(THEME["teal"])

        # Loop standard style indices (0 to 64) and apply base paper
        for style_id in range(64):
            lexer.setPaper(QColor(THEME["base"]), style_id)

        if isinstance(lexer, QsciLexerPython):
            lexer.setColor(comment_color, QsciLexerPython.Comment)
            lexer.setColor(comment_color, QsciLexerPython.CommentBlock)
            lexer.setColor(number_color, QsciLexerPython.Number)
            lexer.setColor(string_color, QsciLexerPython.DoubleQuotedString)
            lexer.setColor(string_color, QsciLexerPython.SingleQuotedString)
            lexer.setColor(string_color, QsciLexerPython.TripleSingleQuotedString)
            lexer.setColor(string_color, QsciLexerPython.TripleDoubleQuotedString)
            lexer.setColor(keyword_color, QsciLexerPython.Keyword)
            lexer.setColor(func_color, QsciLexerPython.ClassName)
            lexer.setColor(func_color, QsciLexerPython.FunctionMethodName)
            lexer.setColor(op_color, QsciLexerPython.Operator)
            lexer.setColor(base_color, QsciLexerPython.Identifier)
            lexer.setColor(QColor(THEME["yellow"]), QsciLexerPython.Decorator)
        elif isinstance(lexer, QsciLexerSQL):
            lexer.setColor(comment_color, QsciLexerSQL.Comment)
            lexer.setColor(comment_color, QsciLexerSQL.CommentLine)
            lexer.setColor(number_color, QsciLexerSQL.Number)
            lexer.setColor(string_color, QsciLexerSQL.SingleQuotedString)
            lexer.setColor(string_color, QsciLexerSQL.DoubleQuotedString)
            lexer.setColor(keyword_color, QsciLexerSQL.Keyword)
            lexer.setColor(op_color, QsciLexerSQL.Operator)
        elif isinstance(lexer, QsciLexerJSON):
            lexer.setColor(number_color, QsciLexerJSON.Number)
            lexer.setColor(string_color, QsciLexerJSON.String)
            lexer.setColor(keyword_color, QsciLexerJSON.Keyword)
            lexer.setColor(func_color, QsciLexerJSON.Property)
            lexer.setColor(op_color, QsciLexerJSON.Operator)
        elif isinstance(lexer, QsciLexerYAML):
            lexer.setColor(comment_color, QsciLexerYAML.Comment)
            lexer.setColor(keyword_color, QsciLexerYAML.Keyword)
            lexer.setColor(base_color, QsciLexerYAML.Identifier)
            lexer.setColor(number_color, QsciLexerYAML.Number)
            lexer.setColor(op_color, QsciLexerYAML.Operator)
        elif isinstance(lexer, QsciLexerBash):
            lexer.setColor(comment_color, QsciLexerBash.Comment)
            lexer.setColor(number_color, QsciLexerBash.Number)
            lexer.setColor(keyword_color, QsciLexerBash.Keyword)
            lexer.setColor(string_color, QsciLexerBash.DoubleQuotedString)
            lexer.setColor(string_color, QsciLexerBash.SingleQuotedString)
            lexer.setColor(op_color, QsciLexerBash.Operator)
            lexer.setColor(func_color, QsciLexerBash.Identifier)

    def _connect_signals(self):
        """Wire editor signals."""
        self.textChanged.connect(self._on_text_changed)
        self.cursorPositionChanged.connect(self._on_cursor_changed)
        self.userListActivated.connect(self._on_user_list_activated)

        if self.lsp_worker:
            self.lsp_worker.completions_ready.connect(self._on_completions_ready)
            self.lsp_worker.signature_ready.connect(self._on_signature_ready)

    def _on_text_changed(self):
        """Debounce autocompletion request on text modification."""
        if not self.filepath.endswith(".py"):
            return
        self._debounce_timer.start()

    def _on_cursor_changed(self, line: int, col: int):
        """Update cursor info and show diagnostic hint if line has lint issue."""
        self.cursor_info_changed.emit(line + 1, col + 1)
        if line in self._diagnostics:
            messages = [f"[{d['code']}] {d['message']}" for d in self._diagnostics[line]]
            self.status_message_requested.emit(" | ".join(messages))

    def _trigger_completion(self):
        """Send completion request to LSP worker thread."""
        if not self.lsp_worker or not self.filepath.endswith(".py"):
            return

        line, col = self.getCursorPosition()
        prefix = self.wordAtLineIndex(line, col - 1)
        # Avoid completing if not typing a word or dot
        line_text = self.text(line)
        char_before = line_text[col - 1] if col > 0 and col <= len(line_text) else ""

        if not prefix and char_before != ".":
            return

        self._current_req_id += 1
        project_dir = os.path.dirname(self.filepath) or os.getcwd()

        # Find .venv python in project directory
        venv_python = os.path.join(project_dir, ".venv", "bin", "python")
        if not os.path.exists(venv_python):
            # Try parent directory
            parent_venv = os.path.join(os.path.dirname(project_dir), ".venv", "bin", "python")
            if os.path.exists(parent_venv):
                venv_python = parent_venv
            else:
                venv_python = ""

        self.lsp_worker.request_completion(
            self._current_req_id,
            self.text(),
            line + 1,
            col,
            self.filepath,
            project_dir,
            venv_python,
            prefix or "",
        )

    def _on_completions_ready(self, req_id: int, prefix: str, items: list):
        """Display autocompletion popup."""
        if req_id != self._current_req_id or not items:
            return
        if not self.hasFocus():
            return
        self.showUserList(self.LIST_ID_AUTOCOMPLETE, items)

    def _on_signature_ready(self, req_id: int, sig_text: str):
        """Display function signature hint in status bar or call tip."""
        if req_id != self._current_req_id or not sig_text:
            return
        self.status_message_requested.emit(f"Signature: {sig_text}")

    def _on_user_list_activated(self, list_id: int, chosen_text: str):
        """Insert selected completion into editor."""
        if list_id != self.LIST_ID_AUTOCOMPLETE:
            return

        line, col = self.getCursorPosition()
        prefix = self.wordAtLineIndex(line, col - 1)
        if prefix:
            self.setSelection(line, col - len(prefix), line, col)
            self.replaceSelectedText(chosen_text)
        else:
            self.insert(chosen_text)

    def set_diagnostics(self, diagnostics: list):
        """Update margin markers with Ruff lint results."""
        self.markerDeleteAll(self.error_marker_id)
        self.markerDeleteAll(self.warning_marker_id)
        self._diagnostics.clear()

        for diag in diagnostics:
            line = diag["line"]
            if line not in self._diagnostics:
                self._diagnostics[line] = []
            self._diagnostics[line].append(diag)

            if diag.get("severity") == "error":
                self.markerAdd(line, self.error_marker_id)
            else:
                self.markerAdd(line, self.warning_marker_id)

    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard shortcuts like Ctrl+S, Ctrl+Shift+F, Ctrl+Space."""
        ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)

        if ctrl and not shift and event.key() == Qt.Key.Key_S:
            self.save_requested.emit()
            event.accept()
            return

        if ctrl and shift and event.key() == Qt.Key.Key_F:
            self.format_requested.emit()
            event.accept()
            return

        if ctrl and not shift and event.key() == Qt.Key.Key_Space:
            self._trigger_completion()
            event.accept()
            return

        super().keyPressEvent(event)
