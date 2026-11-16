"""
PyMint IDE - Main Application Window (JetBrains Air Architecture)
Floating Islands layout (rounded cards, Activity Bar, collapsibles Ctrl+B / Ctrl+J,
Theme / Font / Size real-time selectors, compact RAM Guard status bar menu,
and full Linux Mint native integration).
"""

import os
import shutil
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QLabel,
    QPushButton,
    QComboBox,
    QFileDialog,
    QMessageBox,
    QStatusBar,
    QMenuBar,
    QMenu,
    QScrollArea,
    QFrame,
    QStackedWidget,
    QApplication,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QKeySequence, QFont, QFontDatabase, QIcon

from core.config import APP_NAME, APP_VERSION, settings
from core.lsp_worker import LSPWorker
from core.uv_manager import UVManager
from core.git_manager import GitManager
from core.service_guard import ServiceGuard, MemoryMonitor

from ui.file_tree import FileTreePanel
from ui.editor_tabs import EditorTabs
from ui.terminal_panel import TerminalPanel
from ui.git_panel import GitPanel
from ui.themes import get_theme, get_theme_names, generate_qss


class MainWindow(QMainWindow):
    """PyMint IDE main window featuring Floating Islands architecture."""

    def __init__(self, project_dir: str = ""):
        super().__init__()
        self.project_dir = project_dir or settings.get_last_directory()
        if not os.path.isdir(self.project_dir):
            self.project_dir = os.getcwd()

        self.setWindowTitle(f"{APP_NAME} - {os.path.basename(self.project_dir)}")
        self.setMinimumSize(700, 420)

        # Restore saved window geometry & state
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
                w = min(1140, avail.width() - 40)
                h = min(680, avail.height() - 40)
                self.resize(w, h)
            else:
                self.resize(1050, 650)

        # Active theme
        self.current_theme_name = settings.get_theme()
        self.current_theme = get_theme(self.current_theme_name)

        # Core non-blocking workers and services
        self.lsp_worker = LSPWorker(self)
        self.lsp_worker.start()

        self.uv_manager = UVManager(self)
        self.uv_manager.set_project_dir(self.project_dir)

        self.git_manager = GitManager(self.project_dir, self)
        self.service_guard = ServiceGuard(self)
        self.memory_monitor = MemoryMonitor(self)

        # Service statuses for status bar menu
        self._services_status = {"postgresql": False, "docker": False, "mongod": False, "redis-server": False}
        self._last_ram_info = {"avail_mb": 0, "total_mb": 0, "rss_mb": 0}

        self._init_ui()
        self._init_menu()
        self._init_statusbar()
        self._connect_signals()
        self.apply_theme(self.current_theme_name)

        # Initial checks
        self.service_guard.check_all_services()

    def _wrap_in_scroll(self, widget: QWidget) -> QScrollArea:
        """Wraps tall panels in a scroll area to avoid layout minimum height clamping."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setWidget(widget)
        return scroll

    def _init_ui(self):
        """Constructs the Floating Islands layout."""
        central_widget = QWidget(self)
        central_widget.setObjectName("centralCanvas")
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(8, 6, 8, 8)
        root_layout.setSpacing(8)

        # -------------------------------------------------------------
        # 1. TOP BAR ISLAND (Floating Card with Selectors & Layout Toggles)
        # -------------------------------------------------------------
        self.top_bar = QFrame()
        self.top_bar.setObjectName("topBarCard")
        self.top_bar.setFixedHeight(42)
        top_layout = QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(10, 4, 10, 4)
        top_layout.setSpacing(10)

        # App Brand & Project Name
        lbl_brand = QLabel(f"<b>⚡ {APP_NAME}</b>")
        lbl_brand.setWordWrap(False)
        lbl_brand.setFixedHeight(24)
        lbl_brand.setStyleSheet(f"color: {self.current_theme['accent']}; font-size: 13px;")
        top_layout.addWidget(lbl_brand)

        self.lbl_project_badge = QLabel(f"📁 {os.path.basename(self.project_dir)}")
        self.lbl_project_badge.setWordWrap(False)
        self.lbl_project_badge.setFixedHeight(24)
        self.lbl_project_badge.setMaximumWidth(500)
        self.lbl_project_badge.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.lbl_project_badge.setStyleSheet(f"""
            background-color: {self.current_theme['surface']};
            color: {self.current_theme['text']};
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 11px;
            font-weight: bold;
        """)
        top_layout.addWidget(self.lbl_project_badge)

        # Universal Play (F5 / Ctrl+R) and Detener (Ctrl+C) buttons
        self.btn_run_active = QPushButton("▶ Ejecutar (F5)")
        self.btn_run_active.setObjectName("btnRunActive")
        self.btn_run_active.setToolTip("Guardar y ejecutar archivo activo en terminal (F5 / Ctrl+R)")
        self.btn_run_active.setFixedHeight(26)
        self.btn_run_active.setStyleSheet("""
            QPushButton#btnRunActive {
                background-color: #10B981;
                color: #FFFFFF;
                font-weight: bold;
                border-radius: 4px;
                padding: 2px 10px;
                border: 1px solid #059669;
                font-size: 11px;
            }
            QPushButton#btnRunActive:hover {
                background-color: #059669;
            }
            QPushButton#btnRunActive:pressed {
                background-color: #047857;
            }
        """)
        self.btn_run_active.clicked.connect(self.run_active_file)
        top_layout.addWidget(self.btn_run_active)

        self.btn_stop_active = QPushButton("⏹ Detener")
        self.btn_stop_active.setObjectName("btnStopActive")
        self.btn_stop_active.setToolTip("Detener proceso activo en terminal (Ctrl+C)")
        self.btn_stop_active.setFixedHeight(26)
        self.btn_stop_active.setStyleSheet("""
            QPushButton#btnStopActive {
                background-color: #EF4444;
                color: #FFFFFF;
                font-weight: bold;
                border-radius: 4px;
                padding: 2px 8px;
                border: 1px solid #DC2626;
                font-size: 11px;
            }
            QPushButton#btnStopActive:hover {
                background-color: #DC2626;
            }
            QPushButton#btnStopActive:pressed {
                background-color: #B91C1C;
            }
        """)
        self.btn_stop_active.clicked.connect(lambda: self.terminal_panel.stop_current_process())
        top_layout.addWidget(self.btn_stop_active)

        self.btn_cargo_check = QPushButton("🦀 Cargo Check")
        self.btn_cargo_check.setObjectName("btnCargoCheck")
        self.btn_cargo_check.setToolTip("Ejecutar CARGO_BUILD_JOBS=1 cargo check en terminal")
        self.btn_cargo_check.setFixedHeight(26)
        self.btn_cargo_check.setStyleSheet("""
            QPushButton#btnCargoCheck {
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: bold;
                border-radius: 4px;
                padding: 2px 8px;
                border: 1px solid #1D4ED8;
                font-size: 11px;
            }
            QPushButton#btnCargoCheck:hover {
                background-color: #1D4ED8;
            }
            QPushButton#btnCargoCheck:pressed {
                background-color: #1E40AF;
            }
        """)
        self.btn_cargo_check.clicked.connect(self.cargo_check)
        top_layout.addWidget(self.btn_cargo_check)

        top_layout.addStretch()

        # Theme Selector: QComboBox
        top_layout.addWidget(QLabel("Theme:"))
        self.combo_theme = QComboBox()
        for tname in get_theme_names():
            self.combo_theme.addItem(tname)
        self.combo_theme.setCurrentText(self.current_theme_name)
        self.combo_theme.currentTextChanged.connect(self.apply_theme)
        top_layout.addWidget(self.combo_theme)

        # Font Selector: QComboBox with system monospace fonts
        top_layout.addWidget(QLabel("Font:"))
        self.combo_font = QComboBox()
        self._populate_monospace_fonts()
        saved_font = settings.get_font_family()
        idx_f = self.combo_font.findText(saved_font)
        if idx_f != -1:
            self.combo_font.setCurrentIndex(idx_f)
        self.combo_font.currentTextChanged.connect(self._on_font_changed)
        top_layout.addWidget(self.combo_font)

        # Font Size Selector: QComboBox (9pt to 18pt)
        top_layout.addWidget(QLabel("Size:"))
        self.combo_size = QComboBox()
        for s in [9, 10, 11, 12, 13, 14, 16, 18]:
            self.combo_size.addItem(f"{s}pt", s)
        saved_size = settings.get_font_size()
        idx_s = self.combo_size.findData(saved_size)
        if idx_s != -1:
            self.combo_size.setCurrentIndex(idx_s)
        self.combo_size.currentIndexChanged.connect(self._on_font_size_changed)
        top_layout.addWidget(self.combo_size)

        # Quick Layout Toggles
        btn_toggle_side = QPushButton("◫ Sidebar")
        btn_toggle_side.setToolTip("Alternar panel lateral (Ctrl+B)")
        btn_toggle_side.setFixedHeight(26)
        btn_toggle_side.clicked.connect(self._toggle_sidebar)
        top_layout.addWidget(btn_toggle_side)

        btn_toggle_term = QPushButton("▤ Terminal")
        btn_toggle_term.setToolTip("Alternar terminal integrada (Ctrl+J)")
        btn_toggle_term.setFixedHeight(26)
        btn_toggle_term.clicked.connect(self._toggle_terminal)
        top_layout.addWidget(btn_toggle_term)

        btn_mint_term = QPushButton("↗ Mint")
        btn_mint_term.setToolTip("Abrir Terminal Nativa del Sistema (gnome-terminal)")
        btn_mint_term.setFixedHeight(26)
        btn_mint_term.clicked.connect(lambda: self.terminal_panel.open_native_terminal())
        top_layout.addWidget(btn_mint_term)

        root_layout.addWidget(self.top_bar)

        # -------------------------------------------------------------
        # 2. BODY AREA (Activity Bar + Splitters)
        # -------------------------------------------------------------
        body_container = QWidget()
        body_layout = QHBoxLayout(body_container)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(8)

        # Activity Bar (Left icon dock, 42px wide)
        self.activity_bar = QFrame()
        self.activity_bar.setObjectName("activityBar")
        self.activity_bar.setFixedWidth(44)
        act_layout = QVBoxLayout(self.activity_bar)
        act_layout.setContentsMargins(3, 8, 3, 8)
        act_layout.setSpacing(6)

        # File Explorer Button
        self.btn_act_files = QPushButton("📁")
        self.btn_act_files.setObjectName("activityBtn")
        self.btn_act_files.setToolTip("Explorador de Archivos (Ctrl+B)")
        self.btn_act_files.setFixedHeight(36)
        self.btn_act_files.setProperty("active", "true")
        self.btn_act_files.clicked.connect(lambda: self._select_activity("files"))
        act_layout.addWidget(self.btn_act_files)

        # Git Button
        self.btn_act_git = QPushButton("🌿")
        self.btn_act_git.setObjectName("activityBtn")
        self.btn_act_git.setToolTip("Git & GitHub (Ctrl+Shift+G)")
        self.btn_act_git.setFixedHeight(36)
        self.btn_act_git.setProperty("active", "false")
        self.btn_act_git.clicked.connect(lambda: self._select_activity("git"))
        act_layout.addWidget(self.btn_act_git)

        act_layout.addStretch()

        # Open Project button
        btn_open = QPushButton("📂")
        btn_open.setObjectName("activityBtn")
        btn_open.setToolTip("Abrir otra carpeta...")
        btn_open.setFixedHeight(34)
        btn_open.clicked.connect(self._action_open_folder)
        act_layout.addWidget(btn_open)

        body_layout.addWidget(self.activity_bar)

        # Main Vertical Splitter: Top (Lateral + Editor), Bottom (Terminal)
        self.v_splitter = QSplitter(Qt.Orientation.Vertical)
        self.v_splitter.setHandleWidth(6)
        self.v_splitter.setChildrenCollapsible(False)

        # Horizontal Splitter: Left (Lateral Island), Right (Editor Island)
        self.h_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.h_splitter.setHandleWidth(6)
        self.h_splitter.setChildrenCollapsible(False)

        # -------------------------------------------------------------
        # 3. LATERAL ISLAND (Card with Files / Git Stack)
        # -------------------------------------------------------------
        self.lateral_island = QFrame()
        self.lateral_island.setObjectName("lateralIsland")
        lat_layout = QVBoxLayout(self.lateral_island)
        lat_layout.setContentsMargins(0, 0, 0, 0)
        lat_layout.setSpacing(0)

        # Lateral Island Header
        self.lateral_header = QWidget()
        self.lateral_header.setObjectName("islandHeader")
        lh_layout = QHBoxLayout(self.lateral_header)
        lh_layout.setContentsMargins(8, 4, 8, 4)
        lh_layout.setSpacing(4)

        self.lbl_lateral_title = QLabel("EXPLORER")
        self.lbl_lateral_title.setObjectName("islandHeaderTitle")
        lh_layout.addWidget(self.lbl_lateral_title)

        lh_layout.addStretch()

        btn_collapse_lat = QPushButton("—")
        btn_collapse_lat.setObjectName("islandHeaderBtn")
        btn_collapse_lat.setToolTip("Ocultar barra lateral (Ctrl+B)")
        btn_collapse_lat.setFixedSize(22, 22)
        btn_collapse_lat.clicked.connect(self._toggle_sidebar)
        lh_layout.addWidget(btn_collapse_lat)

        lat_layout.addWidget(self.lateral_header)

        # Stacked Widget: Page 0 = Files, Page 1 = Git
        self.lateral_stack = QStackedWidget()

        # Tab 1: File Explorer
        self.file_tree = FileTreePanel(self.project_dir, self)
        self.lateral_stack.addWidget(self.file_tree)

        # Tab 2: Git Panel (wrapped in scroll area)
        self.git_panel = GitPanel(self.git_manager, self)
        self.lateral_stack.addWidget(self._wrap_in_scroll(self.git_panel))

        lat_layout.addWidget(self.lateral_stack)
        self.h_splitter.addWidget(self.lateral_island)

        # -------------------------------------------------------------
        # 4. EDITOR ISLAND (Central Code Area)
        # -------------------------------------------------------------
        self.editor_island = QFrame()
        self.editor_island.setObjectName("editorIsland")
        ed_layout = QVBoxLayout(self.editor_island)
        ed_layout.setContentsMargins(2, 2, 2, 2)
        ed_layout.setSpacing(0)

        self.editor_tabs = EditorTabs(
            lsp_worker=self.lsp_worker,
            theme_dict=self.current_theme,
            parent=self,
        )
        ed_layout.addWidget(self.editor_tabs)
        self.h_splitter.addWidget(self.editor_island)

        # Splitter sizing
        self.h_splitter.setStretchFactor(0, 0)
        self.h_splitter.setStretchFactor(1, 1)
        self.h_splitter.setSizes([260, 840])

        self.v_splitter.addWidget(self.h_splitter)

        # -------------------------------------------------------------
        # 5. TERMINAL ISLAND (Bottom PTY Terminal)
        # -------------------------------------------------------------
        self.terminal_island = QFrame()
        self.terminal_island.setObjectName("terminalIsland")
        term_layout = QVBoxLayout(self.terminal_island)
        term_layout.setContentsMargins(2, 2, 2, 2)
        term_layout.setSpacing(0)

        self.terminal_panel = TerminalPanel(
            project_dir=self.project_dir,
            theme_dict=self.current_theme,
            parent=self,
        )
        self.terminal_panel.collapse_requested.connect(self._toggle_terminal)
        term_layout.addWidget(self.terminal_panel)

        self.v_splitter.addWidget(self.terminal_island)

        self.v_splitter.setStretchFactor(0, 1)
        self.v_splitter.setStretchFactor(1, 0)
        self.v_splitter.setSizes([450, 180])

        body_layout.addWidget(self.v_splitter)
        root_layout.addWidget(body_container)

    def _populate_monospace_fonts(self):
        """Populates font selector with available system monospace fonts."""
        families = QFontDatabase.families()
        mono_fonts = [f for f in families if QFontDatabase.isFixedPitch(f)]

        popular = ["JetBrains Mono", "Fira Code", "Ubuntu Mono", "DejaVu Sans Mono", "Monospace"]
        added = set()

        for p in popular:
            if p in families:
                self.combo_font.addItem(p)
                added.add(p)

        for m in mono_fonts:
            if m not in added:
                self.combo_font.addItem(m)
                added.add(m)

        if not added:
            self.combo_font.addItem("Monospace")

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

        act_toggle_sidebar = QAction("Toggle Sidebar", self)
        act_toggle_sidebar.setShortcut(QKeySequence("Ctrl+B"))
        act_toggle_sidebar.triggered.connect(self._toggle_sidebar)
        menu_view.addAction(act_toggle_sidebar)

        act_toggle_terminal = QAction("Toggle Terminal", self)
        act_toggle_terminal.setShortcut(QKeySequence("Ctrl+J"))
        act_toggle_terminal.triggered.connect(self._toggle_terminal)
        menu_view.addAction(act_toggle_terminal)

        act_toggle_term_alt = QAction("Toggle Terminal (Backtick)", self)
        act_toggle_term_alt.setShortcut(QKeySequence("Ctrl+`"))
        act_toggle_term_alt.triggered.connect(self._toggle_terminal)
        menu_view.addAction(act_toggle_term_alt)

        menu_view.addSeparator()

        act_toggle_fullscreen = QAction("Toggle Full Screen", self)
        act_toggle_fullscreen.setShortcut(QKeySequence("F11"))
        act_toggle_fullscreen.triggered.connect(self._toggle_fullscreen)
        menu_view.addAction(act_toggle_fullscreen)

        # Run Menu
        menu_run = menubar.addMenu("&Run")

        act_run = QAction("▶ Ejecutar Archivo Activo", self)
        act_run.setShortcuts([QKeySequence("F5"), QKeySequence("Ctrl+R")])
        act_run.triggered.connect(self.run_active_file)
        self.addAction(act_run)
        menu_run.addAction(act_run)

        act_stop = QAction("⏹ Detener Proceso Activo (SIGINT)", self)
        act_stop.setShortcut(QKeySequence("Ctrl+C"))
        act_stop.triggered.connect(self.terminal_panel.stop_current_process)
        menu_run.addAction(act_stop)

        menu_run.addSeparator()

        act_cargo_check = QAction("🦀 Cargo Check", self)
        act_cargo_check.triggered.connect(self.cargo_check)
        menu_run.addAction(act_cargo_check)

        act_cargo_init = QAction("🦀 Nuevo Proyecto Rust (cargo init)", self)
        act_cargo_init.triggered.connect(self.cargo_init_project)
        menu_run.addAction(act_cargo_init)

        menu_run.addSeparator()

        act_run_fastapi = QAction("Run FastAPI", self)
        act_run_fastapi.triggered.connect(self.terminal_panel.run_fastapi)
        menu_run.addAction(act_run_fastapi)

        act_run_django = QAction("Run Django", self)
        act_run_django.triggered.connect(self.terminal_panel.run_django)
        menu_run.addAction(act_run_django)

    def _init_statusbar(self):
        self.status_bar = self.statusBar()
        self.status_bar.setFixedHeight(28)
        self.status_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.lbl_status_msg = QLabel("Ready")
        self.lbl_status_msg.setWordWrap(False)
        self.lbl_status_msg.setFixedHeight(24)
        self.lbl_status_msg.setMaximumWidth(500)
        self.lbl_status_msg.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.status_bar.addWidget(self.lbl_status_msg, stretch=1)

        self.lbl_cursor_pos = QLabel("Ln 1, Col 1")
        self.lbl_cursor_pos.setWordWrap(False)
        self.lbl_cursor_pos.setFixedHeight(24)
        self.lbl_cursor_pos.setMaximumWidth(120)
        self.lbl_cursor_pos.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.lbl_cursor_pos.setStyleSheet("padding: 0 8px;")
        self.status_bar.addPermanentWidget(self.lbl_cursor_pos)

        self.lbl_env = QLabel("Python: System")
        self.lbl_env.setWordWrap(False)
        self.lbl_env.setFixedHeight(24)
        self.lbl_env.setMaximumWidth(200)
        self.lbl_env.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.lbl_env.setStyleSheet("padding: 0 8px;")
        self.status_bar.addPermanentWidget(self.lbl_env)

        # Compact RAM & Services Indicator Button [Servicios ▾]
        self.btn_ram_services = QPushButton("⚡ RAM Libre: Calculando... [Servicios ▾]")
        self.btn_ram_services.setObjectName("ramServicesBtn")
        self.btn_ram_services.setFixedHeight(22)
        self.btn_ram_services.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.btn_ram_services.setToolTip("RAM Guard: Haz clic para encender/apagar PostgreSQL o Docker con 1-clic")
        self.btn_ram_services.clicked.connect(self._show_services_menu)
        self.status_bar.addPermanentWidget(self.btn_ram_services)

        self._update_env_status()

    def set_status_message(self, text: str):
        """Universal status message handler enforcing a single short line (max 90 chars)."""
        clean = " ".join(str(text).splitlines()).strip()
        if len(clean) > 90:
            clean = clean[:87] + "..."
        self.lbl_status_msg.setText(clean)

    def _connect_signals(self):
        # File explorer to editor tabs
        self.file_tree.file_double_clicked.connect(self.editor_tabs.open_file)
        self.file_tree.folder_opened_in_terminal.connect(self.terminal_panel.new_terminal_tab)

        # Editor notifications
        self.editor_tabs.status_message_requested.connect(self.set_status_message)
        self.editor_tabs.active_editor_changed.connect(self._on_active_editor_changed)
        self.editor_tabs.file_saved.connect(lambda _: self.git_manager.refresh_status())

        # Git terminal hand-off
        self.git_panel.run_in_terminal_requested.connect(self._run_git_command_in_terminal)

        # Memory monitor
        self.memory_monitor.memory_updated.connect(self._on_memory_updated)
        self.memory_monitor.check_memory()

        # Service Guard updates
        self.service_guard.service_status_changed.connect(self._on_service_status_changed)

    def _select_activity(self, tab_name: str):
        """Switches lateral island page or toggles it closed if already active."""
        if tab_name == "files":
            if self.lateral_island.isVisible() and self.lateral_stack.currentIndex() == 0:
                self.lateral_island.setVisible(False)
                self.btn_act_files.setProperty("active", "false")
            else:
                self.lateral_island.setVisible(True)
                self.lateral_stack.setCurrentIndex(0)
                self.lbl_lateral_title.setText("EXPLORER")
                self.btn_act_files.setProperty("active", "true")
                self.btn_act_git.setProperty("active", "false")
        elif tab_name == "git":
            if self.lateral_island.isVisible() and self.lateral_stack.currentIndex() == 1:
                self.lateral_island.setVisible(False)
                self.btn_act_git.setProperty("active", "false")
            else:
                self.lateral_island.setVisible(True)
                self.lateral_stack.setCurrentIndex(1)
                self.lbl_lateral_title.setText("GIT & GITHUB")
                self.btn_act_git.setProperty("active", "true")
                self.btn_act_files.setProperty("active", "false")
                self.git_panel.refresh_all()

        # Force style refresh for active property
        self.btn_act_files.style().unpolish(self.btn_act_files)
        self.btn_act_files.style().polish(self.btn_act_files)
        self.btn_act_git.style().unpolish(self.btn_act_git)
        self.btn_act_git.style().polish(self.btn_act_git)

    def _toggle_sidebar(self):
        is_vis = not self.lateral_island.isVisible()
        self.lateral_island.setVisible(is_vis)
        if not is_vis:
            self.btn_act_files.setProperty("active", "false")
            self.btn_act_git.setProperty("active", "false")
        else:
            if self.lateral_stack.currentIndex() == 0:
                self.btn_act_files.setProperty("active", "true")
            else:
                self.btn_act_git.setProperty("active", "true")

        self.btn_act_files.style().unpolish(self.btn_act_files)
        self.btn_act_files.style().polish(self.btn_act_files)
        self.btn_act_git.style().unpolish(self.btn_act_git)
        self.btn_act_git.style().polish(self.btn_act_git)

    def _toggle_terminal(self):
        self.terminal_island.setVisible(not self.terminal_island.isVisible())

    def _run_git_command_in_terminal(self, cmd: str):
        """Executes a git command interactively in the terminal island."""
        self.terminal_island.setVisible(True)
        term = self.terminal_panel.current_terminal() or self.terminal_panel.new_terminal_tab("Git")
        term.setFocus()
        term.write_to_pty(cmd)

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
        self._last_ram_info = {"avail_mb": avail_mb, "total_mb": total_mb, "rss_mb": rss_mb}
        color = self.current_theme["red"] if is_low else (
            self.current_theme["yellow"] if avail_mb < 800 else self.current_theme["green"]
        )
        alert_tag = " ⚠️" if is_low else ""
        self.btn_ram_services.setText(f"⚡ RAM Libre: {avail_mb} MB [Servicios ▾]{alert_tag}")

    def _on_service_status_changed(self, service_name: str, is_active: bool):
        self._services_status[service_name] = is_active

    def _show_services_menu(self):
        """Displays compact popup menu to toggle PostgreSQL and Docker with pkexec."""
        menu = QMenu(self)

        title_action = QAction("⚡ RAM Guard - Servicios del Sistema", self)
        title_action.setEnabled(False)
        menu.addAction(title_action)
        menu.addSeparator()

        # PostgreSQL toggle
        pg_active = self._services_status.get("postgresql", False)
        pg_icon = "● Activo (Detener)" if pg_active else "○ Inactivo (Iniciar)"
        act_pg = QAction(f"PostgreSQL: {pg_icon}", self)
        act_pg.triggered.connect(lambda: self.service_guard.toggle_service("postgresql", pg_active))
        menu.addAction(act_pg)

        # Docker toggle
        dk_active = self._services_status.get("docker", False)
        dk_icon = "● Activo (Detener)" if dk_active else "○ Inactivo (Iniciar)"
        act_dk = QAction(f"Docker Daemon: {dk_icon}", self)
        act_dk.triggered.connect(lambda: self.service_guard.toggle_service("docker", dk_active))
        menu.addAction(act_dk)

        menu.addSeparator()

        # RAM Summary info
        info = self._last_ram_info
        summary = f"Total: {info['total_mb']} MB | IDE RSS: {info['rss_mb']} MB"
        act_sum = QAction(summary, self)
        act_sum.setEnabled(False)
        menu.addAction(act_sum)

        act_refresh = QAction("🔄 Verificar Servicios Ahora", self)
        act_refresh.triggered.connect(self.service_guard.check_all_services)
        menu.addAction(act_refresh)

        # Show menu aligned above/below the status bar button
        menu.exec(self.btn_ram_services.mapToGlobal(self.btn_ram_services.rect().topLeft()))

    def _update_env_status(self):
        venv_py = settings.get_venv_python(self.project_dir)
        if venv_py:
            self.lbl_env.setText(f"Python: <font color='{self.current_theme['green']}'>.venv (Active)</font>")
        else:
            self.lbl_env.setText("Python: System (No .venv)")

    def apply_theme(self, theme_name: str):
        """Switches theme in real-time across UI cards, lexers, and terminal."""
        self.current_theme_name = theme_name
        self.current_theme = get_theme(theme_name)
        settings.set_theme(theme_name)

        # Update QSS
        qss = generate_qss(self.current_theme)
        self.setStyleSheet(qss)

        # Update badges and labels
        self.lbl_project_badge.setStyleSheet(f"""
            background-color: {self.current_theme['surface']};
            color: {self.current_theme['text']};
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 11px;
            font-weight: bold;
        """)

        # Get active font
        font = self._get_current_font()

        # Propagate to subcomponents
        self.editor_tabs.apply_theme(self.current_theme, font)
        self.terminal_panel.apply_theme(self.current_theme, font)
        self.file_tree.apply_theme(self.current_theme)
        if hasattr(self, "git_panel"):
            self.git_panel.apply_theme(self.current_theme)
        self._update_env_status()

    def _get_current_font(self) -> QFont:
        family = settings.get_font_family()
        size = settings.get_font_size()
        f = QFont(family, size)
        f.setFixedPitch(True)
        return f

    def _on_font_changed(self, font_name: str):
        if not font_name:
            return
        settings.set_font_family(font_name)
        font = self._get_current_font()
        self.editor_tabs.apply_theme(self.current_theme, font)
        self.terminal_panel.apply_theme(self.current_theme, font)

    def _on_font_size_changed(self, index: int):
        size = self.combo_size.itemData(index)
        if size:
            settings.set_font_size(int(size))
            font = self._get_current_font()
            self.editor_tabs.apply_theme(self.current_theme, font)
            self.terminal_panel.apply_theme(self.current_theme, font)

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
        folder_name = os.path.basename(folder_path) or folder_path
        self.setWindowTitle(f"{APP_NAME} - {folder_name}")
        self.lbl_project_badge.setText(f"📁 {folder_name}")

        self.file_tree.set_root_path(folder_path)
        self.uv_manager.set_project_dir(folder_path)
        self.git_manager.set_repo_dir(folder_path)
        self.terminal_panel.set_project_dir(folder_path)

        self._update_env_status()
        self.git_panel.refresh_all()

    def _find_cargo_root(self, start_dir: str) -> str | None:
        """Searches directory and parents upwards for Cargo.toml."""
        curr = os.path.abspath(start_dir)
        while curr and curr != os.path.dirname(curr):
            if os.path.isfile(os.path.join(curr, "Cargo.toml")):
                return curr
            curr = os.path.dirname(curr)
        if os.path.isfile(os.path.join(curr, "Cargo.toml")):
            return curr
        return None

    def run_active_file(self):
        """Universal Run (F5 / Ctrl+R): saves and executes active file in terminal island."""
        editor = self.editor_tabs.current_editor()
        if not editor:
            self.set_status_message("No hay ningún archivo abierto para ejecutar")
            return

        filepath = editor.filepath
        if not filepath:
            filepath, _ = QFileDialog.getSaveFileName(
                self, "Guardar archivo antes de ejecutar", self.project_dir
            )
            if not filepath:
                return
            editor.filepath = filepath
            self.editor_tabs.save_file(filepath)
        else:
            self.editor_tabs.save_file(filepath)

        # Step 2: Show terminal if hidden and focus active terminal
        if not self.terminal_island.isVisible():
            self.terminal_island.setVisible(True)

        term = self.terminal_panel.current_terminal() or self.terminal_panel.new_terminal_tab()
        term.setFocus()

        # Step 3: Detect extension and construct command
        ext = os.path.splitext(filepath)[1].lower()
        basename = os.path.basename(filepath).lower()

        if ext == ".py":
            venv_bin = os.path.join(self.project_dir, ".venv", "bin", "python")
            if os.path.isfile(venv_bin):
                cmd = f'.venv/bin/python "{filepath}"'
            else:
                cmd = f'python3 "{filepath}"'
        elif ext == ".rs" or basename == "cargo.toml":
            cargo_dir = self._find_cargo_root(os.path.dirname(filepath))
            if cargo_dir:
                # Caso A: Proyecto Cargo con Cargo.toml
                cmd = f'cd "{cargo_dir}" && CARGO_BUILD_JOBS=1 cargo run'
            else:
                # Caso B: Archivo .rs suelto sin Cargo.toml
                cmd = f'rustc "{filepath}" -o /tmp/pymint_rust_bin && /tmp/pymint_rust_bin'
        elif ext in (".sh", ".bash"):
            cmd = f'bash "{filepath}"'
        else:
            self.set_status_message(f"Tipo de archivo no ejecutable directamente: {ext}")
            return

        self.terminal_panel.send_command_to_terminal(cmd)
        self.set_status_message(f"Ejecutando: {os.path.basename(filepath)}")

    def cargo_check(self):
        """Executes CARGO_BUILD_JOBS=1 cargo check in the integrated terminal."""
        if not self.terminal_island.isVisible():
            self.terminal_island.setVisible(True)

        editor = self.editor_tabs.current_editor()
        curr_dir = os.path.dirname(editor.filepath) if editor and editor.filepath else self.project_dir
        cargo_dir = self._find_cargo_root(curr_dir) or self.project_dir

        cmd = f'cd "{cargo_dir}" && CARGO_BUILD_JOBS=1 cargo check'
        self.terminal_panel.send_command_to_terminal(cmd)
        self.set_status_message("Ejecutando: CARGO_BUILD_JOBS=1 cargo check...")

    def cargo_init_project(self):
        """Initializes a new Rust project with cargo init or creates main.rs template."""
        target_dir = self.project_dir or os.getcwd()
        cargo_toml = os.path.join(target_dir, "Cargo.toml")
        src_dir = os.path.join(target_dir, "src")
        src_main = os.path.join(src_dir, "main.rs")
        flat_main = os.path.join(target_dir, "main.rs")

        template_code = 'fn main() {\n    println!("Hola desde Rust!");\n}\n'

        cargo_bin = settings.get_cargo_path()
        has_cargo = bool(shutil.which(cargo_bin) or os.path.exists(cargo_bin))

        if not os.path.exists(cargo_toml) and has_cargo:
            if not self.terminal_island.isVisible():
                self.terminal_island.setVisible(True)
            self.terminal_panel.send_command_to_terminal(f'cd "{target_dir}" && cargo init')

            os.makedirs(src_dir, exist_ok=True)
            if not os.path.exists(src_main):
                with open(src_main, "w", encoding="utf-8") as f:
                    f.write(template_code)
            target_file = src_main
        else:
            if os.path.exists(src_main):
                target_file = src_main
            elif os.path.exists(flat_main):
                target_file = flat_main
            else:
                target_file = flat_main
                with open(target_file, "w", encoding="utf-8") as f:
                    f.write(template_code)

        self.file_tree.set_root_path(target_dir)
        if os.path.exists(target_file):
            self.editor_tabs.open_file(target_file)
        self.set_status_message("Proyecto Rust inicializado con éxito")

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def closeEvent(self, event):
        """Clean shutdown."""
        settings.set_window_geometry(self.saveGeometry())
        settings.set_window_state(self.saveState())

        self.lsp_worker.stop()
        self.editor_tabs.close_all()
        self.git_manager.stop_all()
        self.service_guard.stop_all()

        for idx in range(self.terminal_panel.tabs.count()):
            term = self.terminal_panel.tabs.widget(idx)
            if hasattr(term, "close"):
                term.close()
        super().closeEvent(event)
