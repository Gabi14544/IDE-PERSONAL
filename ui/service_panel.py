"""
PyMint IDE - RAM Guard & Service Panel
1-Click start/stop controls for Docker, PostgreSQL, MongoDB, Redis,
and Docker Compose runners to preserve hardware memory.
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
)
from PyQt6.QtCore import Qt, QTimer
from core.config import THEME
from core.service_guard import ServiceGuard, MemoryMonitor


class ServiceRow(QWidget):
    """Row widget representing a single Linux system service."""

    def __init__(self, service_name: str, display_name: str, guard: ServiceGuard, parent=None):
        super().__init__(parent)
        self.service_name = service_name
        self.guard = guard
        self.is_active = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        self.indicator = QLabel("●")
        self.indicator.setStyleSheet(f"color: {THEME['overlay0']}; font-size: 14px;")
        layout.addWidget(self.indicator)

        self.lbl_name = QLabel(display_name)
        self.lbl_name.setStyleSheet(f"font-weight: bold; color: {THEME['text']}; font-size: 12px;")
        layout.addWidget(self.lbl_name, stretch=1)

        self.btn_toggle = QPushButton("Start")
        self.btn_toggle.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['surface0']};
                color: {THEME['text']};
                border: 1px solid {THEME['surface1']};
                border-radius: 3px;
                padding: 3px 10px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {THEME['surface1']};
            }}
        """)
        self.btn_toggle.clicked.connect(self._on_toggle_clicked)
        layout.addWidget(self.btn_toggle)

    def set_status(self, active: bool):
        self.is_active = active
        if active:
            self.indicator.setStyleSheet(f"color: {THEME['green']}; font-size: 14px;")
            self.btn_toggle.setText("Stop (Free RAM)")
            self.btn_toggle.setStyleSheet(f"""
                QPushButton {{
                    background-color: {THEME['red']};
                    color: {THEME['crust']};
                    border: none;
                    border-radius: 3px;
                    padding: 3px 10px;
                    font-size: 11px;
                    font-weight: bold;
                }}
            """)
        else:
            self.indicator.setStyleSheet(f"color: {THEME['overlay0']}; font-size: 14px;")
            self.btn_toggle.setText("Start")
            self.btn_toggle.setStyleSheet(f"""
                QPushButton {{
                    background-color: {THEME['surface0']};
                    color: {THEME['text']};
                    border: 1px solid {THEME['surface1']};
                    border-radius: 3px;
                    padding: 3px 10px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: {THEME['surface1']};
                }}
            """)

    def _on_toggle_clicked(self):
        self.guard.toggle_service(self.service_name, self.is_active)


class ServicePanel(QWidget):
    """Control center for database services and Docker containers."""

    def __init__(self, service_guard: ServiceGuard, memory_monitor: MemoryMonitor, project_dir: str = "", parent=None):
        super().__init__(parent)
        self.guard = service_guard
        self.mem_monitor = memory_monitor
        self.project_dir = project_dir

        self.service_rows = {}

        self._init_ui()
        self._connect_signals()

        # Initial check
        self.guard.check_all_services()
        self.guard.refresh_docker_containers()

        # Auto refresh timer (every 10 seconds for services)
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(10000)
        self.poll_timer.timeout.connect(self._on_poll)
        self.poll_timer.start()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # RAM Overview card
        ram_box = QGroupBox("System RAM Guard")
        ram_layout = QVBoxLayout(ram_box)
        self.lbl_ram_summary = QLabel("Available RAM: Calculating...")
        self.lbl_ram_summary.setStyleSheet("font-weight: bold; font-size: 12px;")
        ram_layout.addWidget(self.lbl_ram_summary)

        self.ram_bar = QProgressBar()
        self.ram_bar.setRange(0, 100)
        self.ram_bar.setValue(50)
        self.ram_bar.setTextVisible(False)
        self.ram_bar.setFixedHeight(8)
        self.ram_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {THEME['surface0']};
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {THEME['green']};
                border-radius: 4px;
            }}
        """)
        ram_layout.addWidget(self.ram_bar)
        layout.addWidget(ram_box)

        # Services 1-Click Toggles
        svc_box = QGroupBox("Backend Engines & Services")
        svc_layout = QVBoxLayout(svc_box)
        svc_layout.setSpacing(4)

        services = [
            ("docker", "Docker Daemon"),
            ("postgresql", "PostgreSQL Database"),
            ("mongod", "MongoDB (NoSQL)"),
            ("redis-server", "Redis Cache / Queue"),
        ]

        for s_id, s_name in services:
            row = ServiceRow(s_id, s_name, self.guard, self)
            self.service_rows[s_id] = row
            svc_layout.addWidget(row)

        layout.addWidget(svc_box)

        # Docker Compose & Running Containers
        docker_box = QGroupBox("Active Docker Containers")
        d_layout = QVBoxLayout(docker_box)

        # Compose Buttons
        row_compose = QHBoxLayout()
        btn_compose_up = QPushButton("▲ compose up -d")
        btn_compose_up.setToolTip("Start project containers with docker compose up -d")
        btn_compose_up.setStyleSheet(f"background-color: {THEME['blue']}; color: {THEME['crust']}; font-weight: bold; padding: 4px; border-radius: 3px;")
        btn_compose_up.clicked.connect(lambda: self.guard.compose_up(self.project_dir))
        row_compose.addWidget(btn_compose_up)

        btn_compose_down = QPushButton("▼ compose down")
        btn_compose_down.setToolTip("Stop and remove containers to free RAM")
        btn_compose_down.setStyleSheet(f"background-color: {THEME['red']}; color: {THEME['crust']}; font-weight: bold; padding: 4px; border-radius: 3px;")
        btn_compose_down.clicked.connect(lambda: self.guard.compose_down(self.project_dir))
        row_compose.addWidget(btn_compose_down)

        d_layout.addLayout(row_compose)

        self.list_containers = QListWidget()
        self.list_containers.setStyleSheet(f"background-color: {THEME['mantle']}; color: {THEME['text']}; border: 1px solid {THEME['surface0']};")
        d_layout.addWidget(self.list_containers)

        btn_stop_selected = QPushButton("Stop Selected Container")
        btn_stop_selected.setStyleSheet(f"background-color: {THEME['surface0']}; color: {THEME['peach']}; padding: 4px; border-radius: 3px;")
        btn_stop_selected.clicked.connect(self._on_stop_container)
        d_layout.addWidget(btn_stop_selected)

        layout.addWidget(docker_box, stretch=1)
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
        self.guard.service_status_changed.connect(self._on_service_status)
        self.guard.containers_updated.connect(self._on_containers_updated)
        self.mem_monitor.memory_updated.connect(self._on_memory_updated)

    def set_project_dir(self, path: str):
        self.project_dir = path

    def _on_poll(self):
        self.guard.check_all_services()
        self.guard.refresh_docker_containers()

    def _on_service_status(self, service_name: str, is_active: bool):
        if service_name in self.service_rows:
            self.service_rows[service_name].set_status(is_active)

    def _on_containers_updated(self, containers: list):
        self.list_containers.clear()
        if not containers:
            self.list_containers.addItem("No active containers (RAM is saved)")
            return
        for c in containers:
            self.list_containers.addItem(f"{c['name']} ({c['status']})")

    def _on_stop_container(self):
        item = self.list_containers.currentItem()
        if item:
            name = item.text().split(" ")[0].strip()
            self.guard.stop_container(name)

    def _on_memory_updated(self, avail_mb: int, total_mb: int, rss_mb: int, is_low: bool):
        used_mb = total_mb - avail_mb
        percent_used = int((used_mb / max(1, total_mb)) * 100)
        self.ram_bar.setValue(percent_used)

        color = THEME["red"] if is_low else (THEME["peach"] if percent_used > 80 else THEME["green"])
        self.ram_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {THEME['surface0']};
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 4px;
            }}
        """)

        alert_str = " <font color='#f38ba8'>[LOW RAM ALERT!]</font>" if is_low else ""
        self.lbl_ram_summary.setText(
            f"Free RAM: <font color='{color}'><b>{avail_mb} MB</b></font> / {total_mb} MB (IDE: {rss_mb} MB){alert_str}"
        )
