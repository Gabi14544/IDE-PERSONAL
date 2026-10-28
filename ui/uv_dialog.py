"""
PyMint IDE - UV & Backend Dependencies Panel
Quick interface for uv project initialization, virtual environment setup,
package installations, and 1-click backend presets.
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QPlainTextEdit,
    QGroupBox,
    QGridLayout,
)
from PyQt6.QtGui import QFont
from core.config import THEME
from core.uv_manager import UVManager


class UVPanel(QWidget):
    """Panel for managing Python virtualenvs and Backend packages via uv."""

    def __init__(self, uv_manager: UVManager, parent=None):
        super().__init__(parent)
        self.uv_manager = uv_manager

        self._init_ui()
        self._connect_signals()
        self.update_status()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Status Banner
        self.status_box = QGroupBox("Environment Status")
        status_layout = QVBoxLayout(self.status_box)
        self.lbl_venv = QLabel("• Virtualenv (.venv): Checking...")
        self.lbl_pyproject = QLabel("• pyproject.toml: Checking...")
        status_layout.addWidget(self.lbl_venv)
        status_layout.addWidget(self.lbl_pyproject)

        btn_init = QPushButton("⚡ Initialize Project + venv (uv init & uv venv)")
        btn_init.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['surface0']};
                color: {THEME['blue']};
                border: 1px solid {THEME['blue']};
                border-radius: 4px;
                padding: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {THEME['blue']};
                color: {THEME['crust']};
            }}
        """)
        btn_init.clicked.connect(self._on_init_clicked)
        status_layout.addWidget(btn_init)
        layout.addWidget(self.status_box)

        # Package Management (Add / Remove)
        pkg_box = QGroupBox("Package Manager (uv add / uv remove)")
        pkg_layout = QVBoxLayout(pkg_box)

        input_layout = QHBoxLayout()
        self.txt_package = QLineEdit()
        self.txt_package.setPlaceholderText("Package name (e.g. httpx, celery, pytest)")
        input_layout.addWidget(self.txt_package)

        btn_add = QPushButton("uv add")
        btn_add.setStyleSheet(f"background-color: {THEME['green']}; color: {THEME['crust']}; font-weight: bold; padding: 4px 10px; border-radius: 3px;")
        btn_add.clicked.connect(self._on_add_clicked)
        input_layout.addWidget(btn_add)

        btn_remove = QPushButton("uv remove")
        btn_remove.setStyleSheet(f"background-color: {THEME['red']}; color: {THEME['crust']}; font-weight: bold; padding: 4px 10px; border-radius: 3px;")
        btn_remove.clicked.connect(self._on_remove_clicked)
        input_layout.addWidget(btn_remove)

        pkg_layout.addLayout(input_layout)
        layout.addWidget(pkg_box)

        # 1-Click Backend Presets
        preset_box = QGroupBox("1-Click Backend Stacks (uv add)")
        preset_grid = QGridLayout(preset_box)
        preset_grid.setSpacing(6)

        presets = [
            ("⚡ FastAPI Stack", "FastAPI", "fastapi, uvicorn, pydantic-settings", THEME["teal"]),
            ("🐍 Django Stack", "Django", "django, djangorestframework", THEME["green"]),
            ("🐘 PostgreSQL Stack", "PostgreSQL", "psycopg, sqlalchemy, alembic", THEME["blue"]),
            ("🍃 NoSQL Stack", "NoSQL", "pymongo, motor, redis", THEME["peach"]),
        ]

        for i, (label, name, tooltip, color) in enumerate(presets):
            row = i // 2
            col = i % 2
            btn = QPushButton(label)
            btn.setToolTip(tooltip)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {THEME['surface0']};
                    color: {color};
                    border: 1px solid {color};
                    border-radius: 4px;
                    padding: 8px 6px;
                    font-weight: bold;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: {color};
                    color: {THEME['crust']};
                }}
            """)
            btn.clicked.connect(lambda checked, p=name: self.uv_manager.install_preset(p))
            preset_grid.addWidget(btn, row, col)

        layout.addWidget(preset_box)

        # UV Output Console
        console_box = QGroupBox("uv Output Console")
        console_layout = QVBoxLayout(console_box)
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Monospace", 9))
        self.console.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {THEME['mantle']};
                color: {THEME['text']};
                border: 1px solid {THEME['surface0']};
            }}
        """)
        console_layout.addWidget(self.console)
        layout.addWidget(console_box, stretch=1)

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
                padding-top: 10px;
                font-weight: bold;
                font-size: 11px;
                color: {THEME['subtext1']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }}
            QLineEdit {{
                background-color: {THEME['surface0']};
                color: {THEME['text']};
                border: 1px solid {THEME['surface1']};
                border-radius: 3px;
                padding: 5px;
            }}
        """)

    def _connect_signals(self):
        self.uv_manager.command_output.connect(self._on_output)
        self.uv_manager.project_env_changed.connect(self.update_status)

    def update_status(self):
        has_venv = self.uv_manager.has_venv()
        has_proj = self.uv_manager.has_pyproject()

        if has_venv:
            self.lbl_venv.setText(f"• Virtualenv: <font color='{THEME['green']}'>Active (.venv)</font>")
        else:
            self.lbl_venv.setText(f"• Virtualenv: <font color='{THEME['red']}'>Not found (Click below to create)</font>")

        if has_proj:
            self.lbl_pyproject.setText(f"• pyproject.toml: <font color='{THEME['green']}'>Found</font>")
        else:
            self.lbl_pyproject.setText(f"• pyproject.toml: <font color='{THEME['yellow']}'>Not found</font>")

    def _on_init_clicked(self):
        if not self.uv_manager.has_pyproject():
            self.uv_manager.init_project()
        self.uv_manager.create_venv()

    def _on_add_clicked(self):
        pkg = self.txt_package.text().strip()
        if pkg:
            self.uv_manager.add_packages(pkg.split())
            self.txt_package.clear()

    def _on_remove_clicked(self):
        pkg = self.txt_package.text().strip()
        if pkg:
            self.uv_manager.remove_packages(pkg.split())
            self.txt_package.clear()

    def _on_output(self, text: str):
        self.console.appendPlainText(text.strip("\r"))
        self.console.verticalScrollBar().setValue(self.console.verticalScrollBar().maximum())
