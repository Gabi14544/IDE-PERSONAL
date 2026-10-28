"""
PyMint IDE - Git & GitHub Visual Panel
Provides branch management, commit history ASCII graph, staging controls,
diff inspection, and GitHub synchronization (Push/Pull/Fetch/Clone).
"""

import os
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QInputDialog,
    QMessageBox,
    QSplitter,
    QGroupBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from core.config import THEME
from core.git_manager import GitManager


class GitPanel(QWidget):
    """Side panel for Git operations and GitHub synchronization."""

    file_diff_requested = pyqtSignal(str, bool)

    def __init__(self, git_manager: GitManager, parent=None):
        super().__init__(parent)
        self.git_manager = git_manager

        self._init_ui()
        self._connect_signals()
        self.refresh_all()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Header: Branch Selector & Sync Actions
        branch_box = QGroupBox("Branches & GitHub Sync")
        branch_layout = QVBoxLayout(branch_box)
        branch_layout.setSpacing(6)

        # Branch row
        row_branch = QHBoxLayout()
        self.lbl_branch = QLabel("Branch:")
        self.lbl_branch.setStyleSheet(f"font-weight: bold; color: {THEME['text']};")
        row_branch.addWidget(self.lbl_branch)

        self.combo_branches = QComboBox()
        self.combo_branches.setStyleSheet(f"""
            QComboBox {{
                background-color: {THEME['surface0']};
                color: {THEME['blue']};
                border: 1px solid {THEME['surface1']};
                padding: 3px 6px;
                border-radius: 3px;
                font-weight: bold;
            }}
            QComboBox QAbstractItemView {{
                background-color: {THEME['surface0']};
                color: {THEME['text']};
                selection-background-color: {THEME['surface1']};
            }}
        """)
        self.combo_branches.currentTextChanged.connect(self._on_branch_selected)
        row_branch.addWidget(self.combo_branches, stretch=1)

        btn_new_branch = QPushButton("+ New")
        btn_new_branch.setToolTip("Create new branch (git checkout -b)")
        btn_new_branch.setStyleSheet(f"background-color: {THEME['surface1']}; color: {THEME['text']}; border-radius: 3px; padding: 4px 8px;")
        btn_new_branch.clicked.connect(self._on_create_branch)
        row_branch.addWidget(btn_new_branch)
        branch_layout.addLayout(row_branch)

        # Sync buttons row: Push, Pull, Fetch
        row_sync = QHBoxLayout()
        btn_fetch = QPushButton("🔄 Fetch")
        btn_fetch.setStyleSheet(f"background-color: {THEME['surface0']}; color: {THEME['text']}; padding: 3px 6px; border-radius: 3px;")
        btn_fetch.clicked.connect(self.git_manager.fetch)
        row_sync.addWidget(btn_fetch)

        btn_pull = QPushButton("⬇ Pull")
        btn_pull.setStyleSheet(f"background-color: {THEME['surface0']}; color: {THEME['teal']}; padding: 3px 6px; border-radius: 3px;")
        btn_pull.clicked.connect(self.git_manager.pull)
        row_sync.addWidget(btn_pull)

        btn_push = QPushButton("⬆ Push")
        btn_push.setStyleSheet(f"background-color: {THEME['surface0']}; color: {THEME['peach']}; font-weight: bold; padding: 3px 6px; border-radius: 3px;")
        btn_push.clicked.connect(self.git_manager.push)
        row_sync.addWidget(btn_push)

        btn_clone = QPushButton("🔗 Clone")
        btn_clone.setStyleSheet(f"background-color: {THEME['surface0']}; color: {THEME['mauve']}; padding: 3px 6px; border-radius: 3px;")
        btn_clone.clicked.connect(self._on_clone_clicked)
        row_sync.addWidget(btn_clone)

        branch_layout.addLayout(row_sync)
        layout.addWidget(branch_box)

        # Staging & Changes
        stage_box = QGroupBox("Changes & Staging")
        stage_layout = QVBoxLayout(stage_box)
        stage_layout.setSpacing(4)

        # Stage / Unstage All buttons
        row_stage_btns = QHBoxLayout()
        btn_stage_all = QPushButton("Stage All (+)")
        btn_stage_all.setStyleSheet(f"background-color: {THEME['green']}; color: {THEME['crust']}; font-weight: bold; padding: 3px 6px; border-radius: 3px;")
        btn_stage_all.clicked.connect(self.git_manager.stage_all)
        row_stage_btns.addWidget(btn_stage_all)

        btn_unstage_all = QPushButton("Unstage All (-)")
        btn_unstage_all.setStyleSheet(f"background-color: {THEME['surface1']}; color: {THEME['text']}; padding: 3px 6px; border-radius: 3px;")
        btn_unstage_all.clicked.connect(self.git_manager.unstage_all)
        row_stage_btns.addWidget(btn_unstage_all)

        btn_refresh = QPushButton("⟳")
        btn_refresh.setFixedSize(24, 22)
        btn_refresh.setStyleSheet(f"background-color: {THEME['surface0']}; color: {THEME['text']}; border-radius: 3px;")
        btn_refresh.clicked.connect(self.refresh_all)
        row_stage_btns.addWidget(btn_refresh)
        stage_layout.addLayout(row_stage_btns)

        # Staged files list
        stage_layout.addWidget(QLabel("<font color='#a6e3a1'><b>Staged Changes:</b></font>"))
        self.list_staged = QListWidget()
        self.list_staged.setStyleSheet(f"background-color: {THEME['mantle']}; color: {THEME['text']}; border: 1px solid {THEME['surface0']}; font-size: 11px;")
        self.list_staged.itemDoubleClicked.connect(self._on_staged_item_clicked)
        stage_layout.addWidget(self.list_staged, stretch=1)

        # Unstaged files list
        stage_layout.addWidget(QLabel("<font color='#fab387'><b>Working Tree Changes:</b></font>"))
        self.list_unstaged = QListWidget()
        self.list_unstaged.setStyleSheet(f"background-color: {THEME['mantle']}; color: {THEME['text']}; border: 1px solid {THEME['surface0']}; font-size: 11px;")
        self.list_unstaged.itemDoubleClicked.connect(self._on_unstaged_item_clicked)
        stage_layout.addWidget(self.list_unstaged, stretch=1)

        # Commit input and button
        self.txt_commit = QPlainTextEdit()
        self.txt_commit.setPlaceholderText("Commit message (Ctrl+Enter to commit)")
        self.txt_commit.setMaximumHeight(50)
        self.txt_commit.setStyleSheet(f"background-color: {THEME['surface0']}; color: {THEME['text']}; border: 1px solid {THEME['surface1']}; border-radius: 3px;")
        stage_layout.addWidget(self.txt_commit)

        btn_commit = QPushButton("✔ Commit")
        btn_commit.setStyleSheet(f"background-color: {THEME['blue']}; color: {THEME['crust']}; font-weight: bold; padding: 5px; border-radius: 4px;")
        btn_commit.clicked.connect(self._on_commit_clicked)
        stage_layout.addWidget(btn_commit)

        layout.addWidget(stage_box, stretch=2)

        # Visual Commit History Graph
        graph_box = QGroupBox("Git History Graph (git log --graph)")
        graph_layout = QVBoxLayout(graph_box)
        self.txt_graph = QPlainTextEdit()
        self.txt_graph.setReadOnly(True)
        self.txt_graph.setFont(QFont("Monospace", 9))
        self.txt_graph.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {THEME['mantle']};
                color: {THEME['teal']};
                border: 1px solid {THEME['surface0']};
            }}
        """)
        graph_layout.addWidget(self.txt_graph)
        layout.addWidget(graph_box, stretch=1)

        self._apply_theme()

    def _apply_theme(self):
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {THEME['base']};
                color: {THEME['text']};
            }}
            QGroupBox {{
                border: 1px solid {THEME['surface0']};
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                font-weight: bold;
                font-size: 11px;
                color: {THEME['subtext1']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }}
        """)

    def _connect_signals(self):
        self.git_manager.branches_updated.connect(self._on_branches_updated)
        self.git_manager.status_updated.connect(self._on_status_updated)
        self.git_manager.log_graph_updated.connect(self._on_graph_updated)
        self.git_manager.command_finished.connect(self._on_command_finished)

    def refresh_all(self):
        self.git_manager.refresh_branches()
        self.git_manager.refresh_status()
        self.git_manager.refresh_log_graph()

    def _on_branches_updated(self, current: str, branches: list):
        self.combo_branches.blockSignals(True)
        self.combo_branches.clear()
        for b in branches:
            self.combo_branches.addItem(b)
        self.combo_branches.setCurrentText(current)
        self.combo_branches.blockSignals(False)

    def _on_branch_selected(self, branch: str):
        if branch:
            self.git_manager.checkout_branch(branch)

    def _on_create_branch(self):
        name, ok = QInputDialog.getText(self, "New Branch", "Branch name:")
        if ok and name.strip():
            self.git_manager.create_branch(name.strip())

    def _on_clone_clicked(self):
        url, ok = QInputDialog.getText(self, "Clone Repository", "Git/GitHub Repository URL:")
        if ok and url.strip():
            target_dir = os.path.join(os.path.dirname(self.git_manager.repo_dir), os.path.basename(url.strip()).replace(".git", ""))
            self.git_manager.clone(url.strip(), target_dir)

    def _on_status_updated(self, staged: list, unstaged: list):
        self.list_staged.clear()
        for item in staged:
            self.list_staged.addItem(f"[{item['status']}] {item['file']}")

        self.list_unstaged.clear()
        for item in unstaged:
            self.list_unstaged.addItem(f"[{item['status']}] {item['file']}")

    def _on_staged_item_clicked(self, item: QListWidgetItem):
        # Double clicking staged file un-stages it
        text = item.text()
        filename = text.split("] ", 1)[-1].strip()
        self.git_manager.unstage_file(filename)

    def _on_unstaged_item_clicked(self, item: QListWidgetItem):
        # Double clicking unstaged file stages it
        text = item.text()
        filename = text.split("] ", 1)[-1].strip()
        self.git_manager.stage_file(filename)

    def _on_commit_clicked(self):
        msg = self.txt_commit.toPlainText().strip()
        if not msg:
            QMessageBox.warning(self, "Commit", "Please enter a commit message.")
            return
        self.git_manager.commit(msg)
        self.txt_commit.clear()

    def _on_graph_updated(self, graph_text: str):
        self.txt_graph.setPlainText(graph_text)

    def _on_command_finished(self, cmd_name: str, success: bool, msg: str):
        if not success and msg:
            # Show brief notice without modal freezing
            pass
