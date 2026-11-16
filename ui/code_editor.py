"""
PyMint IDE - Code Editor Component
Powered by QsciScintilla, customized with JetBrains Air Floating Islands themes,
debounced Jedi autocompletion, Ruff margin markers, and multi-language lexers.
"""

import os
import re
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QListView, QToolTip
from PyQt6.QtGui import QColor, QFont, QKeyEvent
from PyQt6.Qsci import (
    QsciScintilla,
    QsciLexerPython,
    QsciLexerSQL,
    QsciLexerJSON,
    QsciLexerYAML,
    QsciLexerBash,
    QsciLexerMarkdown,
    QsciLexerCPP,
    QsciLexerProperties,
)

from core.config import settings, AUTOCOMPLETE_DEBOUNCE_MS
from ui.themes import get_theme, style_lexer


class RustLexer(QsciLexerCPP):
    """Ultra-lightweight Rust syntax lexer based on QsciLexerCPP."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFoldComments(True)
        self.setFoldPreprocessor(True)

    def keywords(self, set_num: int) -> str:
        if set_num == 1:
            # Rust primary keywords
            return (
                "as async await break const continue crate dyn else enum extern "
                "false fn for if impl in let loop match mod move mut pub ref "
                "return self Self static struct super trait true type unsafe use where while yield"
            )
        elif set_num == 2:
            # Rust types, standard macros, and core library constructs
            return (
                "bool char f32 f64 i8 i16 i32 i64 i128 isize u8 u16 u32 u64 u128 usize str "
                "String Vec Option Some None Result Ok Err Box Rc Arc HashMap HashSet "
                "println eprintln format vec panic assert assert_eq todo"
            )
        return ""


RUST_AUTOCOMPLETE_KEYWORDS = [
    # Palabras clave, tipos, macros y métodos esenciales de Rust (0 MB extra RAM)
    "fn", "let", "mut", "const", "pub", "struct", "enum", "impl", "trait", "match",
    "if", "else", "loop", "while", "for", "in", "return", "use", "mod", "crate",
    "super", "self", "Self", "async", "await", "move", "where", "type", "unsafe", "extern",
    "String", "Vec", "Option", "Some", "None", "Result", "Ok", "Err", "Box", "Rc", "Arc",
    "HashMap", "HashSet", "println!", "eprintln!", "format!", "vec!", "panic!",
    "assert!", "assert_eq!", "todo!", "unwrap()", "expect()", "clone()", "iter()",
    "into_iter()", "map()", "filter()", "collect()", "len()", "push()", "pop()",
    "as_str()", "to_string()", "parse()", "is_some()", "is_none()", "is_ok()", "is_err()",
    "u8", "u16", "u32", "u64", "usize", "i8", "i16", "i32", "i64", "isize",
    "f32", "f64", "bool", "char", "str", "std::io", "std::fs",
    "std::collections::HashMap", "std::env", "#[derive(Debug, Clone, PartialEq)]"
]


def extract_rust_symbols(code: str) -> list[str]:
    """Fast regex extraction of identifiers, functions, structs, enums, variables from Rust code."""
    symbols = []
    seen = set()

    def add(item: str):
        if item and item not in seen and len(item) >= 2:
            seen.add(item)
            symbols.append(item)

    # fn <name>
    for m in re.finditer(r"\bfn\s+([a-zA-Z_][a-zA-Z0-9_]*)", code):
        add(m.group(1))
    # struct <Name>
    for m in re.finditer(r"\bstruct\s+([a-zA-Z_][a-zA-Z0-9_]*)", code):
        add(m.group(1))
    # enum <Name>
    for m in re.finditer(r"\benum\s+([a-zA-Z_][a-zA-Z0-9_]*)", code):
        add(m.group(1))
    # trait <Name>
    for m in re.finditer(r"\btrait\s+([a-zA-Z_][a-zA-Z0-9_]*)", code):
        add(m.group(1))
    # type <Name>
    for m in re.finditer(r"\btype\s+([a-zA-Z_][a-zA-Z0-9_]*)", code):
        add(m.group(1))
    # let [mut] <name>
    for m in re.finditer(r"\blet\s+(?:mut\s+)?([a-zA-Z_][a-zA-Z0-9_]*)", code):
        add(m.group(1))
    # const / static <NAME>
    for m in re.finditer(r"\b(?:const|static)\s+([a-zA-Z_][a-zA-Z0-9_]*)", code):
        add(m.group(1))
    # General identifiers of length >= 3
    for m in re.finditer(r"\b([a-zA-Z_][a-zA-Z0-9_]{2,})\b", code):
        add(m.group(1))

    return symbols


class CodeEditor(QsciScintilla):
    """Native code editor with high performance and low memory consumption."""

    save_requested = pyqtSignal()
    format_requested = pyqtSignal()
    cursor_info_changed = pyqtSignal(int, int)  # line, col
    status_message_requested = pyqtSignal(str)

    LIST_ID_AUTOCOMPLETE = 1

    def __init__(self, filepath: str = "", lsp_worker=None, theme_dict: dict = None, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.lsp_worker = lsp_worker
        self.theme = theme_dict or get_theme(settings.get_theme())
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
        """Configure editor behavior and theme colors."""
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

        # Apply theme colors
        self._apply_theme_colors()

        # Autocompletion UI settings
        self.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsNone)  # Controlled via Jedi
        self.setAutoCompletionCaseSensitivity(False)
        self.setAutoCompletionReplaceWord(True)

        # Disable native QScintilla floating calltips (clean signatures shown in status bar)
        self.setCallTipsStyle(QsciScintilla.CallTipsStyle.CallTipsNone)

        # Matched Braces
        self.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)

        # Autocomplete popup styling
        self._apply_autocomplete_style()

    def setToolTip(self, text: str):
        """Universal tooltip limiter ensuring tooltips never exceed 1 line and 90 chars."""
        clean = " ".join(str(text).splitlines()).strip()
        if len(clean) > 90:
            clean = clean[:87] + "..."
        super().setToolTip(clean)

    def _apply_autocomplete_style(self):
        """Applies explicit high-contrast QSS to QScintilla completion popup QListView."""
        is_dark = self.theme.get("is_dark", True)
        if is_dark:
            qss = """
                QListView {
                    background-color: #1E1F22;
                    color: #E4E4E7;
                    border: 1px solid #3B82F6;
                    border-radius: 6px;
                    padding: 4px;
                    outline: none;
                }
                QListView::item {
                    color: #E4E4E7;
                    padding: 3px 8px;
                    border-radius: 4px;
                }
                QListView::item:selected {
                    background-color: #2563EB;
                    color: #FFFFFF;
                    font-weight: bold;
                }
            """
        else:
            qss = """
                QListView {
                    background-color: #FFFFFF;
                    color: #1E293B;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    padding: 4px;
                    outline: none;
                }
                QListView::item {
                    color: #1E293B;
                    padding: 3px 8px;
                    border-radius: 4px;
                }
                QListView::item:selected {
                    background-color: #2563EB;
                    color: #FFFFFF;
                    font-weight: bold;
                }
            """
        self.setStyleSheet(qss)
        for lv in self.findChildren(QListView):
            lv.setStyleSheet(qss)

    def _apply_theme_colors(self):
        """Sets caret, selection, paper, and line colors based on self.theme."""
        th = self.theme
        editor_bg = QColor(th["editor_bg"])
        editor_fg = QColor(th["editor_fg"])

        # Caret & Current Line
        self.setCaretForegroundColor(QColor(th["editor_caret"]))
        self.setCaretWidth(2)
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(QColor(th["editor_current_line"]))

        # Selection Colors
        self.setSelectionBackgroundColor(QColor(th["editor_selection"]))
        self.setSelectionForegroundColor(editor_fg)

        # Base Paper/Color
        self.setPaper(editor_bg)
        self.setColor(editor_fg)

        # Braces
        self.setMatchedBraceBackgroundColor(QColor(th["surface"]))
        self.setMatchedBraceForegroundColor(QColor(th["accent"]))
        self.setUnmatchedBraceForegroundColor(QColor(th["red"]))

        # Margins & Folding: seamless background, no white squares
        self.setMarginsBackgroundColor(editor_bg)
        self.setMarginsForegroundColor(QColor(th["editor_line_num_fg"]))
        self.setFoldMarginColors(editor_bg, editor_bg)

    def _init_margins(self):
        """Setup line numbers, lint diagnostic markers, and clean folding margin."""
        editor_bg = QColor(self.theme["editor_bg"])
        line_fg = QColor(self.theme["editor_line_num_fg"])

        # Margin 0: Line Numbers (blends with editor background)
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginWidth(0, " 0000 ")
        self.setMarginsBackgroundColor(editor_bg)
        self.setMarginsForegroundColor(line_fg)

        # Margin 1: Lint / Diagnostics markers
        self.setMarginType(1, QsciScintilla.MarginType.SymbolMargin)
        self.setMarginWidth(1, 14)
        self.setMarginSensitivity(1, True)
        self.error_marker_id = self.markerDefine(QsciScintilla.MarkerSymbol.Circle)
        self.setMarkerBackgroundColor(QColor(self.theme["red"]), self.error_marker_id)
        self.setMarkerForegroundColor(editor_bg, self.error_marker_id)

        self.warning_marker_id = self.markerDefine(QsciScintilla.MarkerSymbol.RightArrow)
        self.setMarkerBackgroundColor(QColor(self.theme["yellow"]), self.warning_marker_id)
        self.setMarkerForegroundColor(editor_bg, self.warning_marker_id)

        # Margin 2: Code Folding - PlainFoldStyle with seamless background
        self.setFolding(QsciScintilla.FoldStyle.PlainFoldStyle, 2)
        self.setFoldMarginColors(editor_bg, editor_bg)

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
        elif ext == ".rs":
            lexer = RustLexer(self)
        elif ext == ".toml" or basename in ("cargo.toml", "pyproject.toml"):
            lexer = QsciLexerProperties(self)
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
            style_lexer(lexer, ext, self.theme)
            self.setLexer(lexer)

    def apply_theme(self, theme_dict: dict, font: QFont = None):
        """Dynamically applies a new theme and font to editor and active lexer."""
        self.theme = theme_dict
        if font:
            self.setFont(font)

        self._apply_theme_colors()
        self._apply_autocomplete_style()

        # Update markers
        editor_bg = QColor(self.theme["editor_bg"])
        self.setMarkerBackgroundColor(QColor(self.theme["red"]), self.error_marker_id)
        self.setMarkerForegroundColor(editor_bg, self.error_marker_id)
        self.setMarkerBackgroundColor(QColor(self.theme["yellow"]), self.warning_marker_id)
        self.setMarkerForegroundColor(editor_bg, self.warning_marker_id)

        # Restyle lexer
        lexer = self.lexer()
        if lexer:
            if font:
                lexer.setDefaultFont(font)
                lexer.setFont(font)
            ext = os.path.splitext(self.filepath)[1].lower() if self.filepath else ""
            style_lexer(lexer, ext, self.theme)

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
        if not (self.filepath.endswith(".py") or self.filepath.endswith(".rs")):
            return
        self._debounce_timer.start()

    def _on_cursor_changed(self, line: int, col: int):
        """Update cursor info and show diagnostic hint if line has lint issue."""
        self.cursor_info_changed.emit(line + 1, col + 1)
        if line in self._diagnostics:
            messages = [f"[{d['code']}] {d['message']}" for d in self._diagnostics[line]]
            clean = " ".join(" | ".join(messages).splitlines()).strip()
            if len(clean) > 90:
                clean = clean[:87] + "..."
            self.status_message_requested.emit(clean)

    def _trigger_rust_completion(self):
        """Instant low-consumption autocompletion for Rust in memory (0 MB extra RAM)."""
        line, col = self.getCursorPosition()
        prefix = self.wordAtLineIndex(line, col - 1)
        line_text = self.text(line)
        char_before = line_text[col - 1] if col > 0 and col <= len(line_text) else ""

        # Allow trigger on prefix, after '.', '::', or '#'
        if not prefix and char_before not in (".", ":", "#"):
            return

        doc_text = self.text()
        local_symbols = extract_rust_symbols(doc_text)

        candidates = []
        seen = set()

        def add_candidate(item: str):
            if item not in seen:
                seen.add(item)
                candidates.append(item)

        prefix_lower = (prefix or "").lower()

        # If after a dot '.', prioritize methods like unwrap(), clone(), etc.
        if char_before == "." and not prefix:
            for item in RUST_AUTOCOMPLETE_KEYWORDS:
                if "(" in item or item.endswith("()"):
                    add_candidate(item)

        if prefix_lower:
            # First add matching local symbols
            for item in local_symbols:
                if item.lower().startswith(prefix_lower):
                    add_candidate(item)
            # Then add matching Rust essential keywords/types/macros
            for item in RUST_AUTOCOMPLETE_KEYWORDS:
                clean_name = item.lstrip("#[").rstrip("!()")
                if item.lower().startswith(prefix_lower) or clean_name.lower().startswith(prefix_lower):
                    add_candidate(item)
        else:
            for item in RUST_AUTOCOMPLETE_KEYWORDS:
                add_candidate(item)
            for item in local_symbols:
                add_candidate(item)

        if candidates and self.hasFocus():
            self.showUserList(self.LIST_ID_AUTOCOMPLETE, candidates[:60])
            self._apply_autocomplete_style()

    def _trigger_completion(self):
        """Send completion request: in-memory for Rust, LSP worker for Python."""
        if self.filepath.endswith(".rs"):
            self._trigger_rust_completion()
            return

        if not self.lsp_worker or not self.filepath.endswith(".py"):
            return

        line, col = self.getCursorPosition()
        prefix = self.wordAtLineIndex(line, col - 1)
        line_text = self.text(line)
        char_before = line_text[col - 1] if col > 0 and col <= len(line_text) else ""

        if not prefix and char_before != ".":
            return

        self._current_req_id += 1
        project_dir = os.path.dirname(self.filepath) or os.getcwd()
        venv_python = settings.get_venv_python(project_dir)

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
        self._apply_autocomplete_style()

    def _on_signature_ready(self, req_id: int, sig_text: str):
        """Display function signature hint in status bar, strictly capped to 1 line and 90 chars."""
        if req_id != self._current_req_id or not sig_text:
            return
        msg = f"Signature: {sig_text}"
        clean = " ".join(msg.splitlines()).strip()
        if len(clean) > 90:
            clean = clean[:87] + "..."
        self.status_message_requested.emit(clean)

    def _on_user_list_activated(self, list_id: int, chosen_text: str):
        """Insert selected completion into editor."""
        if list_id != self.LIST_ID_AUTOCOMPLETE:
            return

        line, col = self.getCursorPosition()
        prefix = self.wordAtLineIndex(line, col - 1)
        line_text = self.text(line)

        # Handle special prefix characters like '#['
        if chosen_text.startswith("#[") and line_text[:col].rstrip().endswith("#["):
            chosen_text = chosen_text[2:]
        elif chosen_text.startswith("#[") and line_text[:col].rstrip().endswith("#"):
            chosen_text = chosen_text[1:]

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
