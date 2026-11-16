"""
PyMint IDE - File Tree Panel
Lightweight file explorer using QFileSystemModel with QSortFilterProxyModel
to strictly ignore heavy folders (.venv, __pycache__, node_modules, etc.)
"""

import os
import shutil
import subprocess
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTreeView,
    QLabel,
    QPushButton,
    QMenu,
    QInputDialog,
    QMessageBox,
    QApplication,
)
from PyQt6.QtGui import QFileSystemModel, QAction, QIcon
from PyQt6.QtCore import Qt, QSortFilterProxyModel, pyqtSignal, QModelIndex

from core.config import IGNORED_DIRS, IGNORED_EXTENSIONS, THEME


class IgnoreFilterProxyModel(QSortFilterProxyModel):
    """Filters out heavy folders and binary extensions to protect Celeron CPU & RAM."""

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model: QFileSystemModel = self.sourceModel()
        index = model.index(source_row, 0, source_parent)
        name = model.fileName(index)

        # Ignore heavy directories
        if name in IGNORED_DIRS:
            return False

        # Ignore temporary and compiled binary extensions
        for ext in IGNORED_EXTENSIONS:
            if name.endswith(ext):
                return False

        return True


class FileTreePanel(QWidget):
    """File explorer panel with custom filtering and context menu."""

    file_double_clicked = pyqtSignal(str)
    folder_opened_in_terminal = pyqtSignal(str)

    def __init__(self, root_path: str = "", parent=None):
        super().__init__(parent)
        self.root_path = root_path or os.getcwd()

        self._init_ui()
        self.set_root_path(self.root_path)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Header bar
        header_widget = QWidget()
        header_widget.setStyleSheet(f"background-color: {THEME['mantle']}; padding: 4px;")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(8, 4, 8, 4)
        header_layout.setSpacing(4)

        self.title_label = QLabel("EXPLORER")
        self.title_label.setStyleSheet(
            f"color: {THEME['subtext1']}; font-weight: bold; font-size: 11px; letter-spacing: 1px;"
        )
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        self.refresh_btn = QPushButton("⟳")
        self.refresh_btn.setToolTip("Refresh Explorer")
        self.refresh_btn.setFixedSize(22, 22)
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {THEME['text']};
                border: none;
                border-radius: 3px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {THEME['surface0']};
            }}
        """)
        self.refresh_btn.clicked.connect(self.refresh)
        header_layout.addWidget(self.refresh_btn)

        layout.addWidget(header_widget)

        # File system model + Proxy filter
        self.fs_model = QFileSystemModel()
        self.fs_model.setReadOnly(False)

        self.proxy_model = IgnoreFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.fs_model)

        # Tree View
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.proxy_model)
        self.tree_view.setHeaderHidden(True)
        # Hide Size, Type, Date Modified columns (only show Name = column 0)
        for col in range(1, 4):
            self.tree_view.hideColumn(col)

        self.tree_view.setAnimated(False)  # Disabled animation for low-spec CPU performance
        self.tree_view.setIndentation(14)
        self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self._show_context_menu)
        self.tree_view.doubleClicked.connect(self._on_item_double_clicked)

        self._apply_style()
        layout.addWidget(self.tree_view)

    def _apply_style(self, theme_dict: dict = None):
        th = theme_dict or THEME
        bg = th.get("card_bg", th.get("mantle", "#1E1F22"))
        text = th.get("text", "#E4E4E7")
        surface = th.get("surface", th.get("surface0", "#2B2D30"))
        surface_hover = th.get("surface_hover", th.get("surface1", "#36383E"))
        accent = th.get("accent", th.get("blue", "#3B82F6"))

        self.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                color: {text};
            }}
            QTreeView {{
                background-color: transparent;
                color: {text};
                border: none;
                font-size: 12px;
            }}
            QTreeView::item {{
                padding: 3px 4px;
                border-radius: 4px;
            }}
            QTreeView::item:hover {{
                background-color: {surface};
            }}
            QTreeView::item:selected {{
                background-color: {surface_hover};
                color: {accent};
                font-weight: bold;
            }}
        """)

    def apply_theme(self, theme_dict: dict):
        self._apply_style(theme_dict)

    def set_root_path(self, path: str):
        """Set root path for explorer tree."""
        if not os.path.exists(path):
            return
        self.root_path = os.path.abspath(path)
        folder_name = os.path.basename(self.root_path) or self.root_path
        self.title_label.setText(f"PROJECT: {folder_name.upper()}")

        self.fs_model.setRootPath(self.root_path)
        source_index = self.fs_model.index(self.root_path)
        proxy_index = self.proxy_model.mapFromSource(source_index)
        self.tree_view.setRootIndex(proxy_index)

    def refresh(self):
        """Refreshes the file tree model."""
        self.fs_model.setRootPath("")
        self.fs_model.setRootPath(self.root_path)

    def _on_item_double_clicked(self, proxy_index: QModelIndex):
        """Handle opening a file on double click."""
        source_index = self.proxy_model.mapToSource(proxy_index)
        filepath = self.fs_model.filePath(source_index)
        if os.path.isfile(filepath):
            self.file_double_clicked.emit(filepath)

    def _get_selected_path(self) -> str:
        indexes = self.tree_view.selectedIndexes()
        if indexes:
            source_idx = self.proxy_model.mapToSource(indexes[0])
            return self.fs_model.filePath(source_idx)
        return self.root_path

    def _show_context_menu(self, position):
        """Context menu for creating files, deleting, renaming, and opening in terminal."""
        target_path = self._get_selected_path()
        target_dir = target_path if os.path.isdir(target_path) else os.path.dirname(target_path)

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {THEME['surface0']};
                color: {THEME['text']};
                border: 1px solid {THEME['surface1']};
                padding: 4px;
            }}
            QMenu::item {{
                padding: 5px 20px 5px 20px;
                border-radius: 3px;
            }}
            QMenu::item:selected {{
                background-color: {THEME['surface2']};
                color: {THEME['blue']};
            }}
        """)

        act_new_file = menu.addAction("New File...")
        act_new_folder = menu.addAction("New Folder...")
        menu.addSeparator()
        act_rename = menu.addAction("Rename...")
        act_delete = menu.addAction("Delete")
        menu.addSeparator()
        act_copy_path = menu.addAction("Copy Relative Path")
        act_open_term = menu.addAction("Open in Terminal")

        action = menu.exec(self.tree_view.viewport().mapToGlobal(position))
        if action == act_new_file:
            self._action_new_file(target_dir)
        elif action == act_new_folder:
            self._action_new_folder(target_dir)
        elif action == act_rename:
            self._action_rename(target_path)
        elif action == act_delete:
            self._action_delete(target_path)
        elif action == act_copy_path:
            rel = os.path.relpath(target_path, self.root_path)
            QApplication.clipboard().setText(rel)
        elif action == act_open_term:
            self.folder_opened_in_terminal.emit(target_dir)

    def _action_new_file(self, target_dir: str):
        name, ok = QInputDialog.getText(self, "New File", "Enter file name:")
        if ok and name.strip():
            filepath = os.path.join(target_dir, name.strip())
            try:
                with open(filepath, "a", encoding="utf-8"):
                    pass
                self.file_double_clicked.emit(filepath)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create file:\n{e}")

    def _action_new_folder(self, target_dir: str):
        name, ok = QInputDialog.getText(self, "New Folder", "Enter folder name:")
        if ok and name.strip():
            folder_path = os.path.join(target_dir, name.strip())
            try:
                os.makedirs(folder_path, exist_ok=True)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create folder:\n{e}")

    def _action_rename(self, target_path: str):
        old_name = os.path.basename(target_path)
        new_name, ok = QInputDialog.getText(self, "Rename", "Enter new name:", text=old_name)
        if ok and new_name.strip() and new_name.strip() != old_name:
            new_path = os.path.join(os.path.dirname(target_path), new_name.strip())
            try:
                os.rename(target_path, new_path)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not rename:\n{e}")

    def _action_delete(self, target_path: str):
        name = os.path.basename(target_path)
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to permanently delete:\n{name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if os.path.isdir(target_path):
                    shutil.rmtree(target_path)
                else:
                    os.remove(target_path)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete:\n{e}")
