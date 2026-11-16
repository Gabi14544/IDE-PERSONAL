"""
PyMint IDE - Compact native workspace for small Linux laptops.
"""

import os
import shutil

from core.execution import command_for_file
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
    QMenu,
    QScrollArea,
    QFrame,
    QStackedWidget,
    QApplication,
    QSizePolicy,
    QDialog, QFormLayout, QDialogButtonBox, QStyle,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QKeySequence, QFont, QFontDatabase

from core.config import APP_NAME, settings
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
    """Compact native workspace, with expensive tools activated on demand."""

    def __init__(self, project_dir: str = ""):
        super().__init__()
        self.project_dir = project_dir or settings.get_last_directory()
        if not os.path.isdir(self.project_dir):
            self.project_dir = os.getcwd()

        self.setWindowTitle(f"{APP_NAME} - {os.path.basename(self.project_dir)}")
        self.setMinimumSize(640, 400)
        self._cursor_editor = None
        self._closing_confirmed = False

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

        self.uv_manager = UVManager(self)
        self.uv_manager.set_project_dir(self.project_dir)

        self.git_manager = GitManager(self.project_dir, self)
        self.service_guard = ServiceGuard(self)
        self.memory_monitor = MemoryMonitor(self)

        # Service statuses for status bar menu
        self._services_status = {name: None for name in ServiceGuard.SERVICES}
        self._last_ram_info = {"avail_mb": 0, "total_mb": 0, "rss_mb": 0}

        self._init_ui()
        self._init_menu()
        self._init_statusbar()
        self._connect_signals()
        self.apply_theme(self.current_theme_name)

        # System services are checked only when their menu is opened.

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
        central = QWidget(self)
        central.setObjectName("centralCanvas")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.top_bar = QFrame()
        self.top_bar.setObjectName("topBarCard")
        bar = QHBoxLayout(self.top_bar)
        bar.setContentsMargins(14, 6, 10, 6)
        bar.setSpacing(12)
        brand = QLabel("PyMint")
        brand.setObjectName("brandLabel")
        bar.addWidget(brand)
        self.lbl_project_badge = QLabel(os.path.basename(self.project_dir))
        self.lbl_project_badge.setObjectName("mutedLabel")
        self.lbl_project_badge.setMinimumWidth(0)
        self.lbl_project_badge.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        bar.addWidget(self.lbl_project_badge, 1)
        self.btn_run_active = QPushButton("▶  Ejecutar")
        self.btn_run_active.setObjectName("btnRunActive")
        self.btn_run_active.setToolTip("Guardar y ejecutar archivo activo (F5 / Ctrl+R)")
        self.btn_run_active.setEnabled(False)
        self.btn_run_active.clicked.connect(self.run_active_file)
        bar.addWidget(self.btn_run_active)
        preferences = QPushButton("Ajustes")
        preferences.setToolTip("Tema y tipografía")
        preferences.clicked.connect(self._show_preferences)
        bar.addWidget(preferences)
        root.addWidget(self.top_bar)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        self.activity_bar = QFrame()
        self.activity_bar.setObjectName("activityBar")
        self.activity_bar.setFixedWidth(44)
        activities = QVBoxLayout(self.activity_bar)
        activities.setContentsMargins(3, 8, 3, 8)
        activities.setSpacing(6)
        self.btn_act_files = QPushButton("≡")
        self.btn_act_git = QPushButton("⑂")
        for button, title, key in ((self.btn_act_files, "Archivos (Ctrl+B)", "files"),
                                    (self.btn_act_git, "Control de versiones", "git")):
            button.setObjectName("activityBtn")
            button.setToolTip(title)
            button.setAccessibleName(title)
            button.setFixedSize(36, 36)
            button.setProperty("active", "true" if key == "files" else "false")
            button.clicked.connect(lambda checked=False, name=key: self._select_activity(name))
            activities.addWidget(button)
        activities.addStretch()
        terminal_toggle = QPushButton(">_")
        terminal_toggle.setObjectName("activityBtn")
        terminal_toggle.setToolTip("Terminal (Ctrl+J)")
        terminal_toggle.clicked.connect(self._toggle_terminal)
        activities.addWidget(terminal_toggle)
        open_folder = QPushButton()
        open_folder.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        open_folder.setObjectName("activityBtn")
        open_folder.setToolTip("Abrir carpeta (Ctrl+O)")
        open_folder.clicked.connect(self._action_open_folder)
        activities.addWidget(open_folder)
        body.addWidget(self.activity_bar)

        self.h_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.h_splitter.setHandleWidth(3)
        self.h_splitter.setChildrenCollapsible(False)
        self.lateral_island = QFrame()
        self.lateral_island.setObjectName("lateralIsland")
        self.lateral_island.setMinimumWidth(150)
        lateral = QVBoxLayout(self.lateral_island)
        lateral.setContentsMargins(0, 0, 0, 0)
        lateral.setSpacing(0)
        self.lateral_header = QWidget()
        self.lateral_header.setObjectName("islandHeader")
        heading = QHBoxLayout(self.lateral_header)
        heading.setContentsMargins(12, 6, 8, 6)
        self.lbl_lateral_title = QLabel("ARCHIVOS")
        self.lbl_lateral_title.setObjectName("islandHeaderTitle")
        heading.addWidget(self.lbl_lateral_title)
        heading.addStretch()
        collapse = QPushButton("−")
        collapse.setObjectName("islandHeaderBtn")
        collapse.setFixedSize(22, 22)
        collapse.setToolTip("Ocultar panel lateral (Ctrl+B)")
        collapse.clicked.connect(self._toggle_sidebar)
        heading.addWidget(collapse)
        lateral.addWidget(self.lateral_header)
        self.lateral_stack = QStackedWidget()
        self.file_tree = FileTreePanel(self.project_dir, self)
        self.lateral_stack.addWidget(self.file_tree)
        self.git_panel = GitPanel(self.git_manager, self)
        self.lateral_stack.addWidget(self._wrap_in_scroll(self.git_panel))
        lateral.addWidget(self.lateral_stack)
        self.h_splitter.addWidget(self.lateral_island)

        self.v_splitter = QSplitter(Qt.Orientation.Vertical)
        self.v_splitter.setHandleWidth(3)
        self.v_splitter.setChildrenCollapsible(False)
        self.editor_island = QFrame()
        self.editor_island.setObjectName("editorIsland")
        editors = QVBoxLayout(self.editor_island)
        editors.setContentsMargins(0, 0, 0, 0)
        self.editor_stack = QStackedWidget()
        welcome = QWidget()
        welcome.setObjectName("welcomePage")
        welcome_layout = QVBoxLayout(welcome)
        welcome_layout.setContentsMargins(32, 24, 32, 24)
        welcome_layout.addStretch()
        title = QLabel("Tu espacio para crear.")
        title.setObjectName("welcomeTitle")
        title.setWordWrap(True)
        welcome_layout.addWidget(title)
        subtitle = QLabel("Abrí un archivo del explorador y empezá a programar.")
        subtitle.setObjectName("mutedLabel")
        subtitle.setWordWrap(True)
        welcome_layout.addWidget(subtitle)
        hints = QLabel("Ctrl+O    Abrir carpeta\nF5            Ejecutar archivo\nCtrl+J     Mostrar terminal")
        hints.setObjectName("welcomeHints")
        welcome_layout.addWidget(hints)
        welcome_layout.addStretch()
        self.editor_stack.addWidget(welcome)
        self.editor_tabs = EditorTabs(self.lsp_worker, self.current_theme, self)
        self.editor_stack.addWidget(self.editor_tabs)
        editors.addWidget(self.editor_stack)
        self.v_splitter.addWidget(self.editor_island)

        self.terminal_island = QFrame()
        self.terminal_island.setObjectName("terminalIsland")
        terminal_layout = QVBoxLayout(self.terminal_island)
        terminal_layout.setContentsMargins(0, 0, 0, 0)
        self.terminal_panel = TerminalPanel(self.project_dir, self.current_theme, self)
        self.terminal_panel.collapse_requested.connect(self._toggle_terminal)
        terminal_layout.addWidget(self.terminal_panel)
        self.v_splitter.addWidget(self.terminal_island)
        self.v_splitter.setStretchFactor(0, 1)
        self.v_splitter.setStretchFactor(1, 0)
        self.v_splitter.setSizes([480, 180])
        self.h_splitter.addWidget(self.v_splitter)
        self.h_splitter.setStretchFactor(0, 0)
        self.h_splitter.setStretchFactor(1, 1)
        self.h_splitter.setSizes([210, 900])
        body.addWidget(self.h_splitter)
        root.addLayout(body, 1)

    def _show_preferences(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Apariencia")
        form = QFormLayout(dialog)
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(get_theme_names())
        self.combo_theme.setCurrentText(self.current_theme_name)
        self.combo_theme.currentTextChanged.connect(self.apply_theme)
        form.addRow("Tema", self.combo_theme)
        self.combo_font = QComboBox()
        self._populate_monospace_fonts()
        self.combo_font.setCurrentText(settings.get_font_family())
        self.combo_font.currentTextChanged.connect(self._on_font_changed)
        form.addRow("Fuente del editor", self.combo_font)
        self.combo_size = QComboBox()
        for size in [9, 10, 11, 12, 13, 14, 16, 18]:
            self.combo_size.addItem(f"{size} pt", size)
        self.combo_size.setCurrentIndex(self.combo_size.findData(settings.get_font_size()))
        self.combo_size.currentIndexChanged.connect(self._on_font_size_changed)
        form.addRow("Tamaño", self.combo_size)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(dialog.accept)
        form.addRow(close)
        dialog.exec()
        dialog.deleteLater()

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
        menu_file = menubar.addMenu("&Archivo")

        act_open_folder = QAction("Abrir &carpeta…", self)
        act_open_folder.setShortcut(QKeySequence("Ctrl+O"))
        act_open_folder.triggered.connect(self._action_open_folder)
        menu_file.addAction(act_open_folder)

        act_open_file = QAction("Open &Archivo...", self)
        act_open_file.triggered.connect(self._action_open_file)
        menu_file.addAction(act_open_file)

        menu_file.addSeparator()

        act_save = QAction("&Guardar", self)
        act_save.setShortcut(QKeySequence("Ctrl+S"))
        act_save.triggered.connect(lambda: self.editor_tabs.save_file())
        menu_file.addAction(act_save)

        act_save_all = QAction("Guardar &todo", self)
        act_save_all.setShortcut(QKeySequence("Ctrl+Shift+S"))
        act_save_all.triggered.connect(self.editor_tabs.save_all)
        menu_file.addAction(act_save_all)

        menu_file.addSeparator()

        act_exit = QAction("&Salir", self)
        act_exit.setShortcut(QKeySequence("Ctrl+Q"))
        act_exit.triggered.connect(self.close)
        menu_file.addAction(act_exit)

        # Edit Menu
        menu_edit = menubar.addMenu("&Editar")

        act_format = QAction("Formatear código (Ruff)", self)
        act_format.setShortcut(QKeySequence("Ctrl+Shift+F"))
        act_format.triggered.connect(lambda: self.editor_tabs.format_file())
        menu_edit.addAction(act_format)

        # View Menu
        menu_view = menubar.addMenu("&Ver")

        act_toggle_sidebar = QAction("Mostrar panel lateral", self)
        act_toggle_sidebar.setShortcut(QKeySequence("Ctrl+B"))
        act_toggle_sidebar.triggered.connect(self._toggle_sidebar)
        menu_view.addAction(act_toggle_sidebar)

        act_toggle_terminal = QAction("Mostrar terminal", self)
        act_toggle_terminal.setShortcut(QKeySequence("Ctrl+J"))
        act_toggle_terminal.triggered.connect(self._toggle_terminal)
        menu_view.addAction(act_toggle_terminal)

        act_toggle_term_alt = QAction("Mostrar terminal (alternativo)", self)
        act_toggle_term_alt.setShortcut(QKeySequence("Ctrl+`"))
        act_toggle_term_alt.triggered.connect(self._toggle_terminal)
        menu_view.addAction(act_toggle_term_alt)

        menu_view.addSeparator()

        act_toggle_fullscreen = QAction("Pantalla completa", self)
        act_toggle_fullscreen.setShortcut(QKeySequence("F11"))
        act_toggle_fullscreen.triggered.connect(self._toggle_fullscreen)
        menu_view.addAction(act_toggle_fullscreen)

        # Run Menu
        menu_run = menubar.addMenu("&Ejecutar")

        act_run = QAction("Ejecutar archivo activo", self)
        act_run.setShortcuts([QKeySequence("F5"), QKeySequence("Ctrl+R")])
        act_run.triggered.connect(self.run_active_file)
        self.addAction(act_run)
        menu_run.addAction(act_run)

        act_stop = QAction("Detener ejecución", self)
        act_stop.setShortcut(QKeySequence("Shift+F5"))
        act_stop.triggered.connect(self.terminal_panel.stop_current_process)
        menu_run.addAction(act_stop)

        menu_run.addSeparator()

        act_cargo_check = QAction("Comprobar proyecto Rust", self)
        act_cargo_check.triggered.connect(self.cargo_check)
        menu_run.addAction(act_cargo_check)

        act_cargo_init = QAction("Nuevo proyecto Rust", self)
        act_cargo_init.triggered.connect(self.cargo_init_project)
        menu_run.addAction(act_cargo_init)

        menu_run.addSeparator()

    def _init_statusbar(self):
        self.status_bar = self.statusBar()
        self.status_bar.setFixedHeight(28)
        self.status_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.lbl_status_msg = QLabel("Listo")
        self.lbl_status_msg.setWordWrap(False)
        self.lbl_status_msg.setFixedHeight(24)
        self.lbl_status_msg.setMaximumWidth(500)
        self.lbl_status_msg.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.status_bar.addWidget(self.lbl_status_msg, stretch=1)

        self.lbl_cursor_pos = QLabel("Ln 1, Col 1")
        self.lbl_cursor_pos.setWordWrap(False)
        self.lbl_cursor_pos.setFixedHeight(24)
        self.lbl_cursor_pos.setMaximumWidth(120)
        self.lbl_cursor_pos.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.lbl_cursor_pos.setStyleSheet("padding: 0 8px;")
        self.status_bar.addPermanentWidget(self.lbl_cursor_pos)

        self.lbl_env = QLabel("Python: System")
        self.lbl_env.setWordWrap(False)
        self.lbl_env.setFixedHeight(24)
        self.lbl_env.setMaximumWidth(200)
        self.lbl_env.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.lbl_env.setStyleSheet("padding: 0 8px;")
        self.status_bar.addPermanentWidget(self.lbl_env)

        # Compact RAM & Services Indicator Button [Servicios ▾]
        self.btn_ram_services = QPushButton("Servicios")
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
        self.file_tree.folder_opened_in_terminal.connect(
            lambda path: self.terminal_panel.new_terminal_tab(cwd=path)
        )

        # Editor notifications
        self.editor_tabs.status_message_requested.connect(self.set_status_message)
        self.editor_tabs.active_editor_changed.connect(self._on_active_editor_changed)
        self.editor_tabs.file_saved.connect(self._refresh_visible_git)

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
                self.lbl_lateral_title.setText("ARCHIVOS")
                self.btn_act_files.setProperty("active", "true")
                self.btn_act_git.setProperty("active", "false")
        elif tab_name == "git":
            if self.lateral_island.isVisible() and self.lateral_stack.currentIndex() == 1:
                self.lateral_island.setVisible(False)
                self.btn_act_git.setProperty("active", "false")
            else:
                self.lateral_island.setVisible(True)
                self.lateral_stack.setCurrentIndex(1)
                self.lbl_lateral_title.setText("CONTROL DE VERSIONES")
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

    def _refresh_visible_git(self, _filepath):
        if self.lateral_island.isVisible() and self.lateral_stack.currentIndex() == 1:
            self.git_panel.refresh_all()

    def _on_cursor_info(self, line, col):
        self.lbl_cursor_pos.setText(f"Lín {line}, Col {col}")

    def _on_active_editor_changed(self, editor):
        if self._cursor_editor is not None:
            try:
                self._cursor_editor.cursor_info_changed.disconnect(self._on_cursor_info)
            except (TypeError, RuntimeError):
                pass
        self._cursor_editor = editor
        self.editor_stack.setCurrentIndex(1 if editor else 0)
        self.btn_run_active.setEnabled(editor is not None)
        if editor:
            editor.cursor_info_changed.connect(self._on_cursor_info)
            line, col = editor.getCursorPosition()
            self._on_cursor_info(line + 1, col + 1)
        else:
            self.lbl_cursor_pos.setText("")

    def _on_memory_updated(self, avail_mb: int, total_mb: int, rss_mb: int, is_low: bool):
        self._last_ram_info = {"avail_mb": avail_mb, "total_mb": total_mb, "rss_mb": rss_mb}
        alert_tag = " ⚠️" if is_low else ""
        self.btn_ram_services.setText(f"IDE {rss_mb} MB  ·  Servicios{alert_tag}")
        self.btn_ram_services.setToolTip(f"RAM disponible: {avail_mb} MB de {total_mb} MB")

    def _on_service_status_changed(self, service_name: str, is_active: bool):
        self._services_status[service_name] = is_active

    def _show_services_menu(self):
        """Query service states on demand and update the open menu asynchronously."""
        menu = QMenu(self)
        actions = {}
        for service, label in (("postgresql", "PostgreSQL"), ("docker", "Docker")):
            action = menu.addAction(label)
            action.setEnabled(False)
            action.triggered.connect(
                lambda checked=False, name=service: self.service_guard.toggle_service(
                    name, self._services_status.get(name) is True
                )
            )
            actions[service] = (action, label)

        def update(service, active):
            if service in actions:
                action, label = actions[service]
                state = "Detener" if active else "Iniciar"
                action.setText(f"{label} · {state}")
                action.setEnabled(True)

        for service, (action, label) in actions.items():
            state = self._services_status.get(service)
            if state is not None:
                update(service, state)
            else:
                action.setText(f"{label} · Consultando…")
        menu.addSeparator()
        info = self._last_ram_info
        summary = menu.addAction(f"RAM disponible: {info['avail_mb']} MB · IDE: {info['rss_mb']} MB")
        summary.setEnabled(False)
        self.service_guard.service_status_changed.connect(update)
        self.service_guard.check_all_services()
        try:
            menu.exec(self.btn_ram_services.mapToGlobal(self.btn_ram_services.rect().topLeft()))
        finally:
            self.service_guard.service_status_changed.disconnect(update)
            menu.deleteLater()

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
        self.lbl_project_badge.setText(folder_name)

        self.file_tree.set_root_path(folder_path)
        self.uv_manager.set_project_dir(folder_path)
        self.git_manager.set_repo_dir(folder_path)
        self.terminal_panel.set_project_dir(folder_path)

        self._update_env_status()
        self._refresh_visible_git(None)

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
        """Save and run in a dedicated PTY, keeping interactive terminals untouched."""
        editor = self.editor_tabs.current_editor()
        if not editor:
            self.set_status_message("Abrí un archivo para ejecutar")
            return
        if self.terminal_panel.run_is_active():
            self.set_status_message("Ya hay una ejecución activa. Detenela antes de volver a ejecutar.")
            return
        if not self.editor_tabs.save_file(editor.filepath):
            self.set_status_message("No se pudo guardar el archivo; ejecución cancelada")
            return
        try:
            command, cwd = command_for_file(editor.filepath, self.project_dir)
        except ValueError as error:
            self.set_status_message(str(error))
            return
        self.terminal_island.show()
        try:
            self.terminal_panel.run_command(command, cwd, os.path.basename(editor.filepath))
        except OSError as error:
            self.set_status_message(f"No se pudo iniciar la ejecución: {error}")
            return
        self.set_status_message(f"Ejecutando: {os.path.basename(editor.filepath)}")

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
        if not self._closing_confirmed:
            if not self.editor_tabs.confirm_close():
                event.ignore()
                return
            self._closing_confirmed = True
        settings.set_window_geometry(self.saveGeometry())
        settings.set_window_state(self.saveState())

        if not self.lsp_worker.stop():
            event.ignore()
            QTimer.singleShot(50, self.close)
            return
        self.editor_tabs.close_all()
        self.git_manager.stop_all()
        self.service_guard.stop_all()

        for idx in range(self.terminal_panel.tabs.count()):
            term = self.terminal_panel.tabs.widget(idx)
            if hasattr(term, "close"):
                term.close()
        super().closeEvent(event)
