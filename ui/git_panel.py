"""
PyMint IDE - Git Visual Panel (Minimalist Version)
Displays only 2 clean sections:
1. Ramas del Proyecto (Branches) with active branch highlighted.
2. Últimos Commits (Recent Commits log graph).
All modifications (commit, push, pull, add) are driven directly from the terminal.
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from core.git_manager import GitManager
from core.config import settings
from ui.themes import get_theme


class GitPanel(QWidget):
    """Side panel displaying Branches and Recent Commits."""

    run_in_terminal_requested = pyqtSignal(str)

    def __init__(self, git_manager: GitManager, parent=None, theme_dict: dict = None):
        super().__init__(parent)
        self.git_manager = git_manager
        if isinstance(theme_dict, dict):
            self.theme = theme_dict
        else:
            self.theme = get_theme(settings.get_theme())

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # -------------------------------------------------------------
        # SECCIÓN 1: RAMAS (BRANCHES)
        # -------------------------------------------------------------
        header_branches = QHBoxLayout()
        header_branches.setSpacing(6)

        self.lbl_branches = QLabel("RAMAS (BRANCHES)")
        self.lbl_branches.setStyleSheet("font-weight: bold; font-size: 11px; letter-spacing: 0.5px;")
        header_branches.addWidget(self.lbl_branches)

        header_branches.addStretch()

        self.btn_refresh = QPushButton("🔄 Actualizar")
        self.btn_refresh.setToolTip("Refrescar ramas y commits")
        self.btn_refresh.setFixedHeight(24)
        self.btn_refresh.clicked.connect(self.refresh_all)
        header_branches.addWidget(self.btn_refresh)
        layout.addLayout(header_branches)

        self.list_branches = QListWidget()
        self.list_branches.setMaximumHeight(140)
        self.list_branches.itemDoubleClicked.connect(self._on_branch_double_clicked)
        layout.addWidget(self.list_branches)

        # -------------------------------------------------------------
        # SECCIÓN 2: ÚLTIMOS COMMITS (RECENT COMMITS)
        # -------------------------------------------------------------
        self.lbl_commits = QLabel("ÚLTIMOS COMMITS")
        self.lbl_commits.setStyleSheet("font-weight: bold; font-size: 11px; letter-spacing: 0.5px;")
        layout.addWidget(self.lbl_commits)

        self.txt_commits = QPlainTextEdit()
        self.txt_commits.setReadOnly(True)
        self.txt_commits.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.txt_commits.setFont(QFont("Monospace", 9))
        layout.addWidget(self.txt_commits, stretch=1)

        self.apply_theme(self.theme)

    def _connect_signals(self):
        self.git_manager.branches_updated.connect(self._on_branches_updated)
        self.git_manager.log_graph_updated.connect(self._on_commits_updated)

    def refresh_all(self):
        """Fetches branches and commit history."""
        self.git_manager.refresh_branches()
        self.git_manager.refresh_log_graph()

    def _on_branches_updated(self, current: str, branches: list):
        self.list_branches.clear()
        th = self.theme
        color_active = QColor(th.get("green", "#59A869"))
        color_remote = QColor(th.get("text_muted", "#8C929D"))
        color_local = QColor(th.get("text", "#E4E4E7"))

        for b in branches:
            clean = b.strip()
            item = QListWidgetItem()

            if clean.startswith("* "):
                name = clean[2:].strip()
                item.setText(f"● {name} (activa)")
                item.setForeground(color_active)
                f = item.font()
                f.setBold(True)
                item.setFont(f)
            elif clean.startswith("remotes/"):
                item.setText(f"  {clean}")
                item.setForeground(color_remote)
            else:
                item.setText(f"  {clean}")
                item.setForeground(color_local)

            item.setData(Qt.ItemDataRole.UserRole, clean.replace("* ", "").strip())
            self.list_branches.addItem(item)

    def _on_branch_double_clicked(self, item: QListWidgetItem):
        branch = item.data(Qt.ItemDataRole.UserRole)
        if branch:
            self.git_manager.checkout_branch(branch)

    def _on_commits_updated(self, text: str):
        self.txt_commits.setPlainText(text)

    def apply_theme(self, theme_dict: dict):
        """Applies active theme styling, preventing white-on-white text."""
        self.theme = theme_dict
        th = self.theme
        card_bg = th.get("card_bg", "#1E1F22")
        card_border = th.get("card_border", "#2B2D30")
        text = th.get("text", "#E4E4E7")
        text_muted = th.get("text_muted", "#8C929D")
        surface = th.get("surface", "#2B2D30")
        surface_hover = th.get("surface_hover", "#36383E")
        accent = th.get("accent", "#3B82F6")

        self.lbl_branches.setStyleSheet(f"color: {text_muted}; font-weight: bold; font-size: 11px;")
        self.lbl_commits.setStyleSheet(f"color: {text_muted}; font-weight: bold; font-size: 11px;")

        self.list_branches.setStyleSheet(f"""
            QListWidget {{
                background-color: {surface};
                color: {text};
                border: 1px solid {card_border};
                border-radius: 6px;
                padding: 4px;
                outline: none;
                font-size: 12px;
            }}
            QListWidget::item {{
                padding: 4px 6px;
                border-radius: 4px;
            }}
            QListWidget::item:hover {{
                background-color: {surface_hover};
            }}
            QListWidget::item:selected {{
                background-color: {card_bg};
                color: {accent};
                border: 1px solid {accent};
            }}
        """)

        self.txt_commits.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {surface};
                color: {text};
                border: 1px solid {card_border};
                border-radius: 6px;
                padding: 6px;
                font-family: monospace;
                font-size: 11px;
            }}
        """)

        self.btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background-color: {surface};
                color: {text};
                border: 1px solid {card_border};
                border-radius: 5px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {surface_hover};
                border-color: {accent};
            }}
        """)

        # Recolor existing rows without starting Git processes during a theme change.
        for index in range(self.list_branches.count()):
            item = self.list_branches.item(index)
            name = item.data(Qt.ItemDataRole.UserRole)
            color = th["green"] if name == self.git_manager.current_branch else (
                text_muted if name.startswith("remotes/") else text
            )
            item.setForeground(QColor(color))
