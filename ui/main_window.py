"""
PyMint IDE - Main Application Window
Assembles modular native components (QScintilla editor tabs, Linux PTY terminal,
Ruff linter, Jedi worker, UV manager, Git panel, and RAM Guard).
"""

import os
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QTabWidget,
    QLabel,
    QFileDialog,
    QMessageBox,
    QStatusBar,
    QMenuBar,
    QMenu,
    QScrollArea,
    QFrame,
    QApplication,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QKeySequence, QIcon

from core.config import APP_NAME, APP_VERSION, THEME, settings
from core.lsp_worker import LSPWorker
from core.uv_manager import UVManager
from core.git_manager import GitManager
from core.service_guard import ServiceGuard, MemoryMonitor

from ui.file_tree import FileTreePanel
from ui.editor_tabs import EditorTabs
from ui.terminal_panel import TerminalPanel
from ui.git_panel import GitPanel
from ui.uv_dialog import UVPanel
from ui.service_panel import ServicePanel


class MainWindow(QMainWindow):
    """PyMint IDE main window."""

    def __init__(self, project_dir: str = ""):
        super().__init__()
        self.project_dir = project_dir or settings.get_last_directory()
        if not os.path.isdir(self.project_dir):
            self.project_dir = os.getcwd()

        self.setWindowTitle(f"{APP_NAME} - {os.path.basename(self.project_dir)}")
        self.setMinimumSize(600, 360)

        # Restore saved window geometry & state or fit safely to display resolution
        saved_geo = settings.get_window_geometry()
        if saved_geo:
            self.restoreGeometry(saved_geo)
            saved_state = settings.get_window_state()
            if saved_state:
                self.restoreState(saved_state)
        else:
            screen = QApplication.primaryScreen()
            avail = screen.availableGeometry() if screen else None
            if avail:
                w = min(1100, avail.width() - 40)
                h = min(620, avail.height() - 40)
                self.resize(w, h)
            else:
                self.resize(1000, 620)

        # Core non-blocking workers and services
        self.lsp_worker = LSPWorker(self)
        self.lsp_worker.start()

        self.uv_manager = UVManager(self)
        self.uv_manager.set_project_dir(self.project_dir)

        self.git_manager = GitManager(self.project_dir, self)
        self.service_guard = ServiceGuard(self)
        self.memory_monitor = MemoryMonitor(self)

        self._init_ui()
        self._init_menu()
        self._init_statusbar()
        self._connect_signals()

    def _wrap_in_scroll(self, widget: QWidget) -> QScrollArea:
        """Wraps tall panels in a scroll area to prevent window minimum height constraints."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {THEME['mantle']};
            }}
            QScrollBar:vertical {{
                border: none;
                background: {THEME['mantle']};
                width: 8px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {THEME['surface1']};
                min-height: 20px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {THEME['surface2']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        scroll.setWidget(widget)
        return scroll

    def _init_ui(self):
        """Construct splitter layout."""
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Main vertical splitter (Top: Editor+Sidebar, Bottom: Terminal)
        self.v_splitter = QSplitter(Qt.Orientation.Vertical)
        self.v_splitter.setHandleWidth(4)
        self.v_splitter.setChildrenCollapsible(False)

        # Horizontal splitter (Left: Sidebar Panels, Right: Code Editor)
        self.h_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.h_splitter.setHandleWidth(4)
        self.h_splitter.setChildrenCollapsible(False)

        # Left Sidebar (Tabs: Files, Git, UV, RAM Guard)
        self.sidebar_tabs = QTabWidget()
        self.sidebar_tabs.setTabPosition(QTabWidget.TabPosition.West)
        self.sidebar_tabs.setDocumentMode(True)

        # Tab 1: File Explorer
        self.file_tree = FileTreePanel(self.project_dir, self)
        self.sidebar_tabs.addTab(self.file_tree, "Files")

        # Tab 2: Git Panel (wrapped in scroll area)
        self.git_panel = GitPanel(self.git_manager, self)
        self.sidebar_tabs.addTab(self._wrap_in_scroll(self.git_panel), "Git")

        # Tab 3: UV Manager (wrapped in scroll area)
        self.uv_panel = UVPanel(self.uv_manager, self)
        self.sidebar_tabs.addTab(self._wrap_in_scroll(self.uv_panel), "UV")

        # Tab 4: RAM Guard & Services (wrapped in scroll area)
        self.service_panel = ServicePanel(self.service_guard, self.memory_monitor, self.project_dir, self)
        self.sidebar_tabs.addTab(self._wrap_in_scroll(self.service_panel), "RAM Guard")

        self.h_splitter.addWidget(self.sidebar_tabs)

        # Right: Editor Tabs
        self.editor_tabs = EditorTabs(lsp_worker=self.lsp_worker, parent=self)
        self.h_splitter.addWidget(self.editor_tabs)

        # Splitter sizing and responsive stretching
        self.h_splitter.setStretchFactor(0, 0)  # Sidebar keeps user-set width
        self.h_splitter.setStretchFactor(1, 1)  # Editor gets all expanding horizontal space
        self.h_splitter.setSizes([260, 840])

        self.v_splitter.addWidget(self.h_splitter)

        # Bottom: Terminal Panel
        self.terminal_panel = TerminalPanel(project_dir=self.project_dir, parent=self)
        self.terminal_panel.setMinimumHeight(60)
        self.v_splitter.addWidget(self.terminal_panel)

        self.v_splitter.setStretchFactor(0, 1)  # Upper area (Editor+Sidebar) expands vertically
        self.v_splitter.setStretchFactor(1, 0)  # Terminal keeps reasonable height
        self.v_splitter.setSizes([450, 170])

        main_layout.addWidget(self.v_splitter)
        self._apply_global_theme()

    def _apply_global_theme(self):
        """Native dark theme styling with zero web engines."""
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {THEME['base']};
                color: {THEME['text']};
            }}
            QSplitter::handle {{
                background-color: {THEME['surface0']};
            }}
            QSplitter::handle:hover {{
                background-color: {THEME['blue']};
            }}
            QMenuBar {{
                background-color: {THEME['crust']};
                color: {THEME['text']};
                border-bottom: 1px solid {THEME['surface0']};
                padding: 2px;
            }}
            QMenuBar::item {{
                background: transparent;
                padding: 4px 8px;
            }}
            QMenuBar::item:selected {{
                background-color: {THEME['surface0']};
                border-radius: 3px;
            }}
            QMenu {{
                background-color: {THEME['mantle']};
                color: {THEME['text']};
                border: 1px solid {THEME['surface1']};
                padding: 4px;
            }}
            QMenu::item {{
                padding: 4px 20px;
                border-radius: 2px;
            }}
            QMenu::item:selected {{
                background-color: {THEME['surface1']};
                color: {THEME['blue']};
            }}
            QStatusBar {{
                background-color: {THEME['crust']};
                color: {THEME['subtext0']};
                border-top: 1px solid {THEME['surface0']};
                font-size: 11px;
            }}
        """)

    def _init_menu(self):
        menubar = self.menuBar()

        # File Menu
        menu_file = menubar.addMenu("&File")

        act_open_folder = QAction("Open &Folder...", self)
        act_open_folder.setShortcut(QKeySequence("Ctrl+O"))
        act_open_folder.triggered.connect(self._action_open_folder)
        menu_file.addAction(act_open_folder)

        act_open_file = QAction("Open &File...", self)
        act_open_file.triggered.connect(self._action_open_file)
        menu_file.addAction(act_open_file)

        menu_file.addSeparator()

        act_save = QAction("&Save", self)
        act_save.setShortcut(QKeySequence("Ctrl+S"))
        act_save.triggered.connect(lambda: self.editor_tabs.save_file())
        menu_file.addAction(act_save)

        act_save_all = QAction("Save &All", self)
        act_save_all.setShortcut(QKeySequence("Ctrl+Shift+S"))
        act_save_all.triggered.connect(self.editor_tabs.save_all)
        menu_file.addAction(act_save_all)

        menu_file.addSeparator()

        act_exit = QAction("E&xit", self)
        act_exit.setShortcut(QKeySequence("Ctrl+Q"))
        act_exit.triggered.connect(self.close)
        menu_file.addAction(act_exit)

        # Edit Menu
        menu_edit = menubar.addMenu("&Edit")

        act_format = QAction("Format Code (Ruff)", self)
        act_format.setShortcut(QKeySequence("Ctrl+Shift+F"))
        act_format.triggered.connect(lambda: self.editor_tabs.format_file())
        menu_edit.addAction(act_format)

        # View Menu
        menu_view = menubar.addMenu("&View")

        act_toggle_fullscreen = QAction("Toggle Full Screen", self)
        act_toggle_fullscreen.setShortcut(QKeySequence("F11"))
        act_toggle_fullscreen.triggered.connect(self._toggle_fullscreen)
        menu_view.addAction(act_toggle_fullscreen)

        menu_view.addSeparator()

        act_toggle_sidebar = QAction("Toggle Sidebar", self)
        act_toggle_sidebar.setShortcut(QKeySequence("Ctrl+B"))
        act_toggle_sidebar.triggered.connect(self._toggle_sidebar)
        menu_view.addAction(act_toggle_sidebar)

        act_toggle_terminal = QAction("Toggle Terminal", self)
        act_toggle_terminal.setShortcut(QKeySequence("Ctrl+`"))
        act_toggle_terminal.triggered.connect(self._toggle_terminal)
        menu_view.addAction(act_toggle_terminal)

        # Run Menu
        menu_run = menubar.addMenu("&Run")

        act_run_fastapi = QAction("Run FastAPI", self)
        act_run_fastapi.triggered.connect(self.terminal_panel.run_fastapi)
        menu_run.addAction(act_run_fastapi)

        act_run_django = QAction("Run Django", self)
        act_run_django.triggered.connect(self.terminal_panel.run_django)
        menu_run.addAction(act_run_django)

        act_stop = QAction("Stop Active Server (SIGINT)", self)
        act_stop.setShortcut(QKeySequence("Ctrl+C"))
        act_stop.triggered.connect(self.terminal_panel.stop_current_process)
        menu_run.addAction(act_stop)

        # Stacks Menu
        menu_tools = menubar.addMenu("&Backend")
        for preset in ["FastAPI", "Django", "PostgreSQL", "NoSQL"]:
            act = QAction(f"Install {preset} Stack", self)
            act.triggered.connect(lambda checked, p=preset: self.uv_manager.install_preset(p))
            menu_tools.addAction(act)

    def _init_statusbar(self):
        self.status_bar = self.statusBar()

        self.lbl_status_msg = QLabel("Ready")
        self.status_bar.addWidget(self.lbl_status_msg, stretch=1)

        self.lbl_cursor_pos = QLabel("Ln 1, Col 1")
        self.lbl_cursor_pos.setStyleSheet("padding: 0 8px;")
        self.status_bar.addPermanentWidget(self.lbl_cursor_pos)

        self.lbl_env = QLabel("Python: System")
        self.lbl_env.setStyleSheet(f"padding: 0 8px; color: {THEME['subtext1']};")
        self.status_bar.addPermanentWidget(self.lbl_env)

        self.lbl_ram = QLabel("RAM: Calculating...")
        self.lbl_ram.setStyleSheet("padding: 0 8px; font-weight: bold;")
        self.status_bar.addPermanentWidget(self.lbl_ram)

        self._update_env_status()

    def _connect_signals(self):
        # File explorer to tabs
        self.file_tree.file_double_clicked.connect(self.editor_tabs.open_file)
        self.file_tree.folder_opened_in_terminal.connect(self.terminal_panel.new_terminal_tab)

        # Editor notifications
        self.editor_tabs.status_message_requested.connect(self.lbl_status_msg.setText)
        self.editor_tabs.active_editor_changed.connect(self._on_active_editor_changed)
        self.editor_tabs.file_saved.connect(lambda _: self.git_manager.refresh_status())

        # Memory monitor
        self.memory_monitor.memory_updated.connect(self._on_memory_updated)
        self.memory_monitor.check_memory()

        # UV manager updates
        self.uv_manager.project_env_changed.connect(self._update_env_status)

    def _on_active_editor_changed(self, editor):
        if editor:
            editor.cursor_info_changed.connect(
                lambda line, col: self.lbl_cursor_pos.setText(f"Ln {line}, Col {col}")
            )
            line, col = editor.getCursorPosition()
            self.lbl_cursor_pos.setText(f"Ln {line + 1}, Col {col + 1}")
        else:
            self.lbl_cursor_pos.setText("")

    def _on_memory_updated(self, avail_mb: int, total_mb: int, rss_mb: int, is_low: bool):
        color = THEME["red"] if is_low else (THEME["peach"] if avail_mb < 800 else THEME["green"])
        alert_tag = " ⚠️ LOW RAM" if is_low else ""
        self.lbl_ram.setText(
            f"RAM Free: <font color='{color}'><b>{avail_mb} MB</b></font> / {total_mb} MB | IDE: {rss_mb} MB{alert_tag}"
        )

    def _update_env_status(self):
        venv_py = self.uv_manager.get_venv_python()
        if venv_py:
            self.lbl_env.setText(f"Python: <font color='{THEME['green']}'>.venv (Active)</font>")
        else:
            self.lbl_env.setText("Python: System (No .venv)")

    def _action_open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Open Project Directory", self.project_dir)
        if folder:
            self.set_project_directory(folder)

    def _action_open_file(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Open File", self.project_dir)
        if filepath:
            self.editor_tabs.open_file(filepath)

    def set_project_directory(self, folder_path: str):
        self.project_dir = folder_path
        settings.set_last_directory(folder_path)
        self.setWindowTitle(f"{APP_NAME} - {os.path.basename(folder_path)}")

        self.file_tree.set_root_path(folder_path)
        self.uv_manager.set_project_dir(folder_path)
        self.git_manager.set_repo_dir(folder_path)
        self.service_panel.set_project_dir(folder_path)
        self.terminal_panel.set_project_dir(folder_path)

        self._update_env_status()
        self.git_panel.refresh_all()
        self.uv_panel.update_status()

    def _toggle_sidebar(self):
        self.sidebar_tabs.setVisible(not self.sidebar_tabs.isVisible())

    def _toggle_terminal(self):
        self.terminal_panel.setVisible(not self.terminal_panel.isVisible())

    def _toggle_fullscreen(self):
        """Toggle fullscreen mode (F11)."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def closeEvent(self, event):
        """Gracefully stop LSP background thread and terminals before exit."""
        # Save geometry and state
        settings.set_window_geometry(self.saveGeometry())
        settings.set_window_state(self.saveState())

        self.lsp_worker.stop()
        self.editor_tabs.close_all()
        self.git_manager.stop_all()
        self.service_guard.stop_all()
        # Cleanly close all terminal PTY tabs
        for idx in range(self.terminal_panel.tabs.count()):
            term = self.terminal_panel.tabs.widget(idx)
            if hasattr(term, "close"):
                term.close()
        super().closeEvent(event)
