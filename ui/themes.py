"""
PyMint IDE - Visual Themes Management (JetBrains Air Architecture)
Provides 4 complete themes: JetBrains Air Dark, JetBrains Air Light,
Cursor Midnight Dark, and VS Code Light Hybrid.
"""

from pathlib import Path

from PyQt6.QtGui import QColor
from PyQt6.Qsci import (
    QsciLexerPython,
    QsciLexerSQL,
    QsciLexerJSON,
    QsciLexerYAML,
    QsciLexerBash,
    QsciLexerMarkdown,
    QsciLexerCPP,
    QsciLexerProperties,
)

THEMES = {
    "JetBrains Air Dark": {
        "name": "JetBrains Air Dark",
        "is_dark": True,
        "canvas_bg": "#111317",
        "card_bg": "#1E1F22",
        "card_border": "#2B2D30",
        "header_bg": "#18191C",
        "text": "#E4E4E7",
        "text_muted": "#8C929D",
        "accent": "#3B82F6",
        "accent_hover": "#2563EB",
        "surface": "#2B2D30",
        "surface_hover": "#36383E",
        "input_bg": "#18191C",
        # Editor colors
        "editor_bg": "#1E1F22",
        "editor_fg": "#E4E4E7",
        "editor_current_line": "#26282E",
        "editor_selection": "#2E436E",
        "editor_caret": "#FFFFFF",
        "editor_line_num_bg": "#1E1F22",
        "editor_line_num_fg": "#4E5157",
        # Lexer tokens
        "syntax_comment": "#7A7E85",
        "syntax_string": "#6AAB73",
        "syntax_keyword": "#CF8E6D",
        "syntax_func": "#56A8F5",
        "syntax_class": "#E0A86E",
        "syntax_number": "#2AACB8",
        "syntax_operator": "#BCBEC4",
        "syntax_identifier": "#E4E4E7",
        "syntax_decorator": "#B389FF",
        # Terminal colors
        "terminal_bg": "#1E1F22",
        "terminal_fg": "#E4E4E7",
        # Palette colors
        "green": "#59A869",
        "yellow": "#E5B567",
        "red": "#E06C75",
        "teal": "#2AACB8",
        "blue": "#3B82F6",
        "peach": "#fab387",
        "mauve": "#cba6f7",
    },
    "JetBrains Air Light": {
        "name": "JetBrains Air Light",
        "is_dark": False,
        "canvas_bg": "#EEF2F6",
        "card_bg": "#FFFFFF",
        "card_border": "#CBD5E1",
        "header_bg": "#F8FAFC",
        "text": "#1E293B",
        "text_muted": "#64748B",
        "accent": "#2563EB",
        "accent_hover": "#1D4ED8",
        "surface": "#F1F5F9",
        "surface_hover": "#E2E8F0",
        "input_bg": "#F8FAFC",
        # Editor colors
        "editor_bg": "#FFFFFF",
        "editor_fg": "#1E293B",
        "editor_current_line": "#F8FAFC",
        "editor_selection": "#BFDBFE",
        "editor_caret": "#0F172A",
        "editor_line_num_bg": "#FFFFFF",
        "editor_line_num_fg": "#94A3B8",
        # Lexer tokens
        "syntax_comment": "#94A3B8",
        "syntax_string": "#16A34A",
        "syntax_keyword": "#0284C7",
        "syntax_func": "#2563EB",
        "syntax_class": "#7C3AED",
        "syntax_number": "#D97706",
        "syntax_operator": "#475569",
        "syntax_identifier": "#1E293B",
        "syntax_decorator": "#9333EA",
        # Terminal colors
        "terminal_bg": "#FFFFFF",
        "terminal_fg": "#1E293B",
        # Palette colors
        "green": "#16A34A",
        "yellow": "#D97706",
        "red": "#DC2626",
        "teal": "#0D9488",
        "blue": "#2563EB",
        "peach": "#EA580C",
        "mauve": "#7C3AED",
    },
    "Cursor Midnight Dark": {
        "name": "Cursor Midnight Dark",
        "is_dark": True,
        "canvas_bg": "#09090B",
        "card_bg": "#121215",
        "card_border": "#27272A",
        "header_bg": "#0D0D10",
        "text": "#FAFAFA",
        "text_muted": "#A1A1AA",
        "accent": "#38BDF8",
        "accent_hover": "#0EA5E9",
        "surface": "#27272A",
        "surface_hover": "#3F3F46",
        "input_bg": "#0D0D10",
        # Editor colors
        "editor_bg": "#121215",
        "editor_fg": "#FAFAFA",
        "editor_current_line": "#18181B",
        "editor_selection": "#27272A",
        "editor_caret": "#38BDF8",
        "editor_line_num_bg": "#121215",
        "editor_line_num_fg": "#52525B",
        # Lexer tokens
        "syntax_comment": "#71717A",
        "syntax_string": "#4ADE80",
        "syntax_keyword": "#C084FC",
        "syntax_func": "#60A5FA",
        "syntax_class": "#F472B6",
        "syntax_number": "#FB923C",
        "syntax_operator": "#94A3B8",
        "syntax_identifier": "#FAFAFA",
        "syntax_decorator": "#E879F9",
        # Terminal colors
        "terminal_bg": "#121215",
        "terminal_fg": "#FAFAFA",
        # Palette colors
        "green": "#4ADE80",
        "yellow": "#FBBF24",
        "red": "#F87171",
        "teal": "#2DD4BF",
        "blue": "#38BDF8",
        "peach": "#FB923C",
        "mauve": "#C084FC",
    },
    "VS Code Light Hybrid": {
        "name": "VS Code Light Hybrid",
        "is_dark": False,
        "canvas_bg": "#F3F3F3",
        "card_bg": "#FFFFFF",
        "card_border": "#E5E7EB",
        "header_bg": "#F9FAFB",
        "text": "#1F2937",
        "text_muted": "#6B7280",
        "accent": "#0284C7",
        "accent_hover": "#0369A1",
        "surface": "#F3F4F6",
        "surface_hover": "#E5E7EB",
        "input_bg": "#FFFFFF",
        # Editor colors
        "editor_bg": "#FFFFFF",
        "editor_fg": "#1F2937",
        "editor_current_line": "#F8FAFC",
        "editor_selection": "#BAE6FD",
        "editor_caret": "#0284C7",
        "editor_line_num_bg": "#FFFFFF",
        "editor_line_num_fg": "#94A3B8",
        # Lexer tokens
        "syntax_comment": "#64748B",
        "syntax_string": "#059669",
        "syntax_keyword": "#7C3AED",
        "syntax_func": "#0284C7",
        "syntax_class": "#2563EB",
        "syntax_number": "#EA580C",
        "syntax_operator": "#334155",
        "syntax_identifier": "#1F2937",
        "syntax_decorator": "#8B5CF6",
        # Terminal colors (Hybrid Dark Terminal)
        "terminal_bg": "#18181B",
        "terminal_fg": "#F4F4F5",
        # Palette colors
        "green": "#10B981",
        "yellow": "#F59E0B",
        "red": "#EF4444",
        "teal": "#14B8A6",
        "blue": "#0284C7",
        "peach": "#EA580C",
        "mauve": "#8B5CF6",
    },
}

# Neutral surfaces and a restrained blue accent, sized for 1366 × 768 displays.
THEMES["Graphite"] = {
    **THEMES["JetBrains Air Dark"],
    "name": "Graphite", "canvas_bg": "#15171c", "card_bg": "#1b1e24",
    "header_bg": "#20232a", "card_border": "#2d323c",
    "text": "#dce1ea", "text_muted": "#929baa", "accent": "#82aaff",
    "accent_hover": "#6b96ef", "surface": "#252a33", "surface_hover": "#303744",
    "input_bg": "#171a20", "editor_bg": "#1b1e24", "editor_fg": "#dce1ea",
    "editor_line_num_bg": "#1b1e24", "editor_line_num_fg": "#697383",
    "editor_current_line": "#232832", "editor_selection": "#344666",
    "terminal_bg": "#171a20", "terminal_fg": "#dce1ea",
    "syntax_keyword": "#c3a6ff", "syntax_string": "#a2c98d", "syntax_comment": "#7b8797",
    "syntax_func": "#82aaff", "syntax_number": "#e5bc8a",
}
DEFAULT_THEME_NAME = "Graphite"


def get_theme_names() -> list:
    return [DEFAULT_THEME_NAME] + [name for name in THEMES if name != DEFAULT_THEME_NAME]


def get_theme(name: str) -> dict:
    return THEMES.get(name, THEMES[DEFAULT_THEME_NAME])


def generate_qss(theme: dict) -> str:
    """Compact native workspace; no effects or animated surfaces."""
    t = theme
    close_icon = (Path(__file__).resolve().parents[1] / "assets" / "close-tab.svg").as_posix()
    return f"""
        QWidget {{ color: {t['text']}; font-family: 'Noto Sans', 'DejaVu Sans', sans-serif; font-size: 12px; }}
        QMainWindow, QWidget#centralCanvas {{ background: {t['canvas_bg']}; }}
        QDialog, QMenu {{ background: {t['card_bg']}; }}
        QFrame#topBarCard {{ background: {t['header_bg']}; border-bottom: 1px solid {t['card_border']}; }}
        QFrame#activityBar {{ background: {t['canvas_bg']}; border-right: 1px solid {t['card_border']}; }}
        QFrame#lateralIsland {{ background: {t['header_bg']}; }}
        QFrame#editorIsland, QWidget#welcomePage {{ background: {t['editor_bg']}; }}
        QFrame#terminalIsland {{ background: {t['terminal_bg']}; border-top: 1px solid {t['card_border']}; }}
        QLabel#brandLabel {{ font-size: 15px; font-weight: 600; }}
        QLabel#mutedLabel, QLabel#islandHeaderTitle {{ color: {t['text_muted']}; }}
        QLabel#islandHeaderTitle {{ font-size: 10px; font-weight: 600; letter-spacing: 1px; }}
        QLabel#welcomeTitle {{ font-size: 28px; font-weight: 600; }}
        QLabel#welcomeHints {{ color: {t['text_muted']}; font-size: 12px; padding-top: 24px; }}
        QWidget#islandHeader {{ background: {t['header_bg']}; border-bottom: 1px solid {t['card_border']}; }}
        QPushButton, QToolButton {{ background: transparent; color: {t['text']}; border: 1px solid transparent;
            border-radius: 4px; padding: 5px 10px; }}
        QPushButton:hover, QToolButton:hover {{ background: {t['surface_hover']}; }}
        QPushButton:pressed {{ background: {t['surface']}; }}
        QPushButton:disabled {{ color: {t['text_muted']}; }}
        QPushButton:focus, QToolButton:focus {{ border: 1px solid {t['accent']}; }}
        QPushButton#btnRunActive {{ background: {t['accent']}; color: {t['canvas_bg']}; font-weight: 600; padding: 5px 14px; }}
        QPushButton#btnRunActive:hover {{ background: {t['accent_hover']}; }}
        QPushButton#btnRunActive:disabled {{ background: {t['surface']}; color: {t['text_muted']}; }}
        QPushButton#activityBtn {{ color: {t['text_muted']}; font-size: 20px; padding: 4px; border-radius: 3px; }}
        QPushButton#activityBtn[active="true"] {{ color: {t['accent']}; background: {t['surface']}; border-left: 2px solid {t['accent']}; }}
        QPushButton#islandHeaderBtn {{ color: {t['text_muted']}; padding: 0; font-size: 14px; }}
        QSplitter::handle {{ background: {t['card_border']}; }}
        QSplitter::handle:hover {{ background: {t['accent']}; }}
        QMenuBar {{ background: {t['canvas_bg']}; padding: 2px 6px; }}
        QMenuBar::item {{ padding: 4px 9px; background: transparent; }}
        QMenuBar::item:selected, QMenu::item:selected {{ background: {t['surface_hover']}; }}
        QMenu {{ border: 1px solid {t['card_border']}; padding: 4px; }}
        QMenu::item {{ padding: 6px 26px 6px 12px; }}
        QMenu::separator {{ height: 1px; background: {t['card_border']}; margin: 4px; }}
        QLineEdit, QComboBox, QListView, QListWidget, QPlainTextEdit {{ background: {t['input_bg']};
            color: {t['text']}; border: 1px solid {t['card_border']}; border-radius: 3px;
            selection-background-color: {t['editor_selection']}; selection-color: {t['text']}; }}
        QComboBox {{ padding: 5px 8px; min-width: 100px; }}
        QComboBox QAbstractItemView {{ background: {t['card_bg']}; color: {t['text']}; selection-background-color: {t['surface_hover']}; }}
        QTabWidget::pane {{ border: none; }}
        QTabBar {{ background: {t['header_bg']}; }}
        QTabBar::tab {{ background: {t['header_bg']}; color: {t['text_muted']}; padding: 7px 14px;
            border: none; border-bottom: 2px solid transparent; }}
        QTabBar::tab:selected {{ background: {t['card_bg']}; color: {t['text']}; border-bottom: 2px solid {t['accent']}; }}
        QTabBar::close-button {{ image: url("{close_icon}"); width: 12px; height: 12px; }}
        QTabBar::close-button:hover {{ background: {t['surface_hover']}; }}
        QTabBar::tab:hover:!selected {{ background: {t['surface']}; }}
        QTreeView {{ background: transparent; border: none; outline: none; }}
        QTreeView::item {{ padding: 3px; }}
        QTreeView::item:selected {{ background: {t['surface_hover']}; }}
        QScrollBar:vertical {{ width: 8px; background: transparent; margin: 0; }}
        QScrollBar:horizontal {{ height: 8px; background: transparent; margin: 0; }}
        QScrollBar::handle {{ background: {t['surface_hover']}; border-radius: 3px; min-height: 24px; min-width: 24px; }}
        QScrollBar::handle:hover {{ background: {t['text_muted']}; }}
        QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
        QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
        QStatusBar {{ background: {t['header_bg']}; color: {t['text_muted']}; border-top: 1px solid {t['card_border']}; }}
        QStatusBar QLabel, QPushButton#ramServicesBtn {{ color: {t['text_muted']}; font-size: 11px; }}
        QStatusBar::item {{ border: none; }}
        QToolTip {{ background: {t['card_bg']}; color: {t['text']}; border: 1px solid {t['card_border']}; padding: 4px; }}
    """


def style_lexer(lexer, ext: str, theme: dict):
    """Applies theme colors to Scintilla lexer tokens."""
    if not lexer:
        return

    editor_bg = QColor(theme["editor_bg"])
    editor_fg = QColor(theme["editor_fg"])
    comment_color = QColor(theme["syntax_comment"])
    string_color = QColor(theme["syntax_string"])
    keyword_color = QColor(theme["syntax_keyword"])
    func_color = QColor(theme["syntax_func"])
    class_color = QColor(theme["syntax_class"])
    number_color = QColor(theme["syntax_number"])
    op_color = QColor(theme["syntax_operator"])
    dec_color = QColor(theme["syntax_decorator"])

    # Reset all base styles to match editor canvas
    for style_id in range(64):
        lexer.setPaper(editor_bg, style_id)
        lexer.setColor(editor_fg, style_id)

    lexer.setDefaultPaper(editor_bg)
    lexer.setDefaultColor(editor_fg)
    lexer.setPaper(editor_bg)
    lexer.setColor(editor_fg)

    if isinstance(lexer, QsciLexerPython):
        lexer.setColor(comment_color, QsciLexerPython.Comment)
        lexer.setColor(comment_color, QsciLexerPython.CommentBlock)
        lexer.setColor(number_color, QsciLexerPython.Number)
        lexer.setColor(string_color, QsciLexerPython.DoubleQuotedString)
        lexer.setColor(string_color, QsciLexerPython.SingleQuotedString)
        lexer.setColor(string_color, QsciLexerPython.TripleSingleQuotedString)
        lexer.setColor(string_color, QsciLexerPython.TripleDoubleQuotedString)
        lexer.setColor(keyword_color, QsciLexerPython.Keyword)
        lexer.setColor(class_color, QsciLexerPython.ClassName)
        lexer.setColor(func_color, QsciLexerPython.FunctionMethodName)
        lexer.setColor(op_color, QsciLexerPython.Operator)
        lexer.setColor(editor_fg, QsciLexerPython.Identifier)
        lexer.setColor(dec_color, QsciLexerPython.Decorator)
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
        lexer.setColor(editor_fg, QsciLexerYAML.Identifier)
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
    elif isinstance(lexer, QsciLexerMarkdown):
        lexer.setColor(keyword_color, QsciLexerMarkdown.Header1)
        lexer.setColor(keyword_color, QsciLexerMarkdown.Header2)
        lexer.setColor(keyword_color, QsciLexerMarkdown.Header3)
        lexer.setColor(string_color, QsciLexerMarkdown.Link)
        lexer.setColor(comment_color, QsciLexerMarkdown.BlockQuote)
    elif isinstance(lexer, QsciLexerCPP):
        lexer.setColor(comment_color, QsciLexerCPP.Comment)
        lexer.setColor(comment_color, QsciLexerCPP.CommentLine)
        lexer.setColor(comment_color, QsciLexerCPP.CommentDoc)
        lexer.setColor(comment_color, QsciLexerCPP.CommentLineDoc)
        lexer.setColor(number_color, QsciLexerCPP.Number)
        lexer.setColor(string_color, QsciLexerCPP.DoubleQuotedString)
        lexer.setColor(string_color, QsciLexerCPP.SingleQuotedString)
        lexer.setColor(string_color, QsciLexerCPP.RawString)
        lexer.setColor(string_color, QsciLexerCPP.VerbatimString)
        lexer.setColor(keyword_color, QsciLexerCPP.Keyword)
        lexer.setColor(class_color, QsciLexerCPP.KeywordSet2)
        lexer.setColor(dec_color, QsciLexerCPP.PreProcessor)
        lexer.setColor(op_color, QsciLexerCPP.Operator)
        lexer.setColor(editor_fg, QsciLexerCPP.Identifier)
    elif isinstance(lexer, QsciLexerProperties):
        lexer.setColor(comment_color, QsciLexerProperties.Comment)
        lexer.setColor(class_color, QsciLexerProperties.Section)
        lexer.setColor(func_color, QsciLexerProperties.Key)
        lexer.setColor(op_color, QsciLexerProperties.Assignment)
        lexer.setColor(string_color, QsciLexerProperties.DefaultValue)
        lexer.setColor(editor_fg, QsciLexerProperties.Default)
