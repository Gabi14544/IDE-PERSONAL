#!/usr/bin/env python3
"""
PyMint IDE - Entry Point
Ultra-lightweight native Python Backend IDE optimized for Linux Mint & low-resource hardware.
"""

import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QFont

from ui.main_window import MainWindow
from core.config import APP_NAME, APP_ORG


def main():
    # Performance tuning for low-spec Intel Atom/Celeron hardware
    QApplication.setOrganizationName(APP_ORG)
    QApplication.setApplicationName(APP_NAME)

    # Initialize QApplication
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Set default monospace font
    app_font = QFont("Monospace", 10)
    app.setFont(app_font)

    # Parse initial project directory or file argument
    project_dir = os.getcwd()
    initial_file = None

    if len(sys.argv) > 1:
        target = os.path.abspath(sys.argv[1])
        if os.path.isdir(target):
            project_dir = target
        elif os.path.isfile(target):
            project_dir = os.path.dirname(target)
            initial_file = target

    window = MainWindow(project_dir=project_dir)

    if initial_file:
        window.editor_tabs.open_file(initial_file)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
