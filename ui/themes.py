"""
PyMint IDE - Visual Themes Management (JetBrains Air Architecture)
Provides 4 complete themes: JetBrains Air Dark, JetBrains Air Light,
Cursor Midnight Dark, and VS Code Light Hybrid.
"""

from PyQt6.QtGui import QColor, QFont
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

DEFAULT_THEME_NAME = "JetBrains Air Dark"


def get_theme_names() -> list:
    return list(THEMES.keys())


def get_theme(name: str) -> dict:
    return THEMES.get(name, THEMES[DEFAULT_THEME_NAME])


def generate_qss(theme: dict) -> str:
    """Generates the full modern 'Floating Islands' QSS stylesheet."""
    canvas_bg = theme["canvas_bg"]
    card_bg = theme["card_bg"]
    card_border = theme["card_border"]
    header_bg = theme["header_bg"]
    text = theme["text"]
    text_muted = theme["text_muted"]
    accent = theme["accent"]
    accent_hover = theme["accent_hover"]
    surface = theme["surface"]
    surface_hover = theme["surface_hover"]
    input_bg = theme["input_bg"]

    is_dark = theme.get("is_dark", True)
    if is_dark:
        list_view_qss = """
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
        list_view_qss = """
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

    return f"""
        /* Base canvas background */
        QMainWindow, QWidget#centralCanvas {{
            background-color: {canvas_bg};
            color: {text};
        }}

        /* Floating Island Cards */
        QFrame#topBarCard, QFrame#lateralIsland, QFrame#editorIsland, QFrame#terminalIsland, QFrame#activityBar {{
            background-color: {card_bg};
            border: 1px solid {card_border};
            border-radius: 10px;
        }}

        /* Activity Bar Buttons */
        QPushButton#activityBtn {{
            background-color: transparent;
            color: {text_muted};
            border: none;
            border-radius: 8px;
            font-size: 16px;
            padding: 8px 4px;
        }}
        QPushButton#activityBtn:hover {{
            background-color: {surface};
            color: {text};
        }}
        QPushButton#activityBtn[active="true"] {{
            background-color: {surface};
            color: {accent};
            border-left: 3px solid {accent};
        }}

        /* Island Header Bars */
        QWidget#islandHeader {{
            background-color: {header_bg};
            border-top-left-radius: 9px;
            border-top-right-radius: 9px;
            border-bottom: 1px solid {card_border};
            padding: 4px 8px;
        }}
        QLabel#islandHeaderTitle {{
            color: {text_muted};
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 0.5px;
        }}

        /* Compact Header Buttons (—, +, etc.) */
        QPushButton#islandHeaderBtn {{
            background-color: transparent;
            color: {text_muted};
            border: none;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
            padding: 2px 6px;
        }}
        QPushButton#islandHeaderBtn:hover {{
            background-color: {surface};
            color: {text};
        }}

        /* Splitters */
        QSplitter::handle {{
            background-color: transparent;
        }}

        /* Buttons */
        QPushButton {{
            background-color: {surface};
            color: {text};
            border: 1px solid {card_border};
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 12px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {surface_hover};
            border-color: {accent};
        }}
        QPushButton:pressed {{
            background-color: {accent};
            color: #FFFFFF;
        }}
        QPushButton#accentBtn {{
            background-color: {accent};
            color: #FFFFFF;
            border: 1px solid {accent};
            font-weight: bold;
        }}
        QPushButton#accentBtn:hover {{
            background-color: {accent_hover};
        }}
        QPushButton#btnRunActive {{
            background-color: #10B981;
            color: #FFFFFF;
            font-weight: bold;
            border-radius: 4px;
            padding: 2px 10px;
            border: 1px solid #059669;
            font-size: 11px;
        }}
        QPushButton#btnRunActive:hover {{
            background-color: #059669;
        }}
        QPushButton#btnRunActive:pressed {{
            background-color: #047857;
        }}
        QPushButton#btnStopActive {{
            background-color: #EF4444;
            color: #FFFFFF;
            font-weight: bold;
            border-radius: 4px;
            padding: 2px 8px;
            border: 1px solid #DC2626;
            font-size: 11px;
        }}
        QPushButton#btnStopActive:hover {{
            background-color: #DC2626;
        }}
        QPushButton#btnStopActive:pressed {{
            background-color: #B91C1C;
        }}
        QPushButton#btnCargoCheck {{
            background-color: #2563EB;
            color: #FFFFFF;
            font-weight: bold;
            border-radius: 4px;
            padding: 2px 8px;
            border: 1px solid #1D4ED8;
            font-size: 11px;
        }}
        QPushButton#btnCargoCheck:hover {{
            background-color: #1D4ED8;
        }}

        /* Input Controls */
        QLineEdit, QPlainTextEdit, QTextEdit {{
            background-color: {input_bg};
            color: {text};
            border: 1px solid {card_border};
            border-radius: 6px;
            padding: 4px 8px;
            selection-background-color: {accent};
            selection-color: #FFFFFF;
        }}
        QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{
            border: 1px solid {accent};
        }}

        /* QComboBox */
        QComboBox {{
            background-color: {surface};
            color: {text};
            border: 1px solid {card_border};
            border-radius: 6px;
            padding: 3px 8px;
            font-size: 11px;
            font-weight: 500;
            min-height: 22px;
        }}
        QComboBox:hover {{
            border-color: {accent};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 16px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {card_bg};
            color: {text};
            border: 1px solid {card_border};
            selection-background-color: {accent};
            selection-color: #FFFFFF;
            border-radius: 4px;
            padding: 4px;
        }}

        /* Labels */
        QLabel {{
            color: {text};
        }}
        QLabel#mutedLabel {{
            color: {text_muted};
            font-size: 11px;
        }}

        /* Autocomplete suggestions and List Views */
{list_view_qss}

        /* List Widgets */
        QListWidget, QTreeView {{
            background-color: transparent;
            color: {text};
            border: none;
            outline: none;
        }}
        QListWidget::item, QTreeView::item {{
            padding: 4px 6px;
            border-radius: 4px;
        }}
        QListWidget::item:hover, QTreeView::item:hover {{
            background-color: {surface};
        }}
        QListWidget::item:selected, QTreeView::item:selected {{
            background-color: {surface_hover};
            color: {accent};
            font-weight: bold;
        }}

        /* QTabWidget */
        QTabWidget::pane {{
            border: none;
            background: transparent;
        }}
        QTabBar::tab {{
            background-color: transparent;
            color: {text_muted};
            padding: 6px 12px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            border: 1px solid transparent;
            margin-right: 2px;
            font-size: 11px;
        }}
        QTabBar::tab:hover:!selected {{
            background-color: {surface};
            color: {text};
        }}
        QTabBar::tab:selected {{
            background-color: {card_bg};
            color: {accent};
            border: 1px solid {card_border};
            border-bottom: 2px solid {accent};
            font-weight: bold;
        }}

        /* Scrollbars */
        QScrollBar:vertical {{
            border: none;
            background: transparent;
            width: 6px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: {card_border};
            min-height: 20px;
            border-radius: 3px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {accent};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar:horizontal {{
            border: none;
            background: transparent;
            height: 6px;
            margin: 0px;
        }}
        QScrollBar::handle:horizontal {{
            background: {card_border};
            min-width: 20px;
            border-radius: 3px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {accent};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}

        /* Menu Bar & Menus */
        QMenuBar {{
            background-color: transparent;
            color: {text};
            border: none;
            padding: 2px;
        }}
        QMenuBar::item {{
            background: transparent;
            padding: 4px 8px;
            border-radius: 4px;
        }}
        QMenuBar::item:selected {{
            background-color: {surface};
            color: {text};
        }}
        QMenu {{
            background-color: {card_bg};
            color: {text};
            border: 1px solid {card_border};
            border-radius: 8px;
            padding: 4px;
        }}
        QMenu::item {{
            padding: 6px 22px 6px 10px;
            border-radius: 4px;
            font-size: 12px;
        }}
        QMenu::item:selected {{
            background-color: {accent};
            color: #FFFFFF;
        }}
        QMenu::separator {{
            height: 1px;
            background: {card_border};
            margin: 4px 8px;
        }}

        /* Status Bar */
        QStatusBar {{
            background-color: transparent;
            color: {text_muted};
            border-top: 1px solid {card_border};
            font-size: 11px;
            padding: 2px 4px;
        }}
        QStatusBar::item {{
            border: none;
        }}
        QPushButton#ramServicesBtn {{
            background-color: {surface};
            color: {text};
            border: 1px solid {card_border};
            border-radius: 5px;
            padding: 2px 8px;
            font-size: 11px;
            font-weight: bold;
        }}
        QPushButton#ramServicesBtn:hover {{
            border-color: {accent};
            color: {accent};
        }}

        /* Group Box */
        QGroupBox {{
            border: 1px solid {card_border};
            border-radius: 6px;
            margin-top: 10px;
            padding-top: 10px;
            font-size: 11px;
            font-weight: bold;
            color: {text_muted};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 8px;
            padding: 0 4px;
        }}
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
