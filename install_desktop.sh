#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
MAIN_PY="$SCRIPT_DIR/main.py"
ICON_PATH="$SCRIPT_DIR/assets/pymint-icon.svg"
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/pymint-ide.desktop"

mkdir -p "$DESKTOP_DIR"
chmod +x "$MAIN_PY"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=PyMint IDE
GenericName=Python Backend IDE
Comment=Ultra-lightweight native Python Backend IDE optimized for Linux Mint
Exec=$VENV_PYTHON $MAIN_PY %F
Icon=$ICON_PATH
Terminal=false
Categories=Development;IDE;TextEditor;
MimeType=text/x-python;text/plain;application/json;application/x-yaml;text/x-sql;
Keywords=python;ide;fastapi;django;backend;mint;cinnamon;
StartupNotify=true
StartupWMClass=pymint ide
EOF

chmod +x "$DESKTOP_FILE"

if command -v update-desktop-database > /dev/null 2>&1; then
    update-desktop-database "$DESKTOP_DIR" || true
fi

echo "=========================================================="
echo " PyMint IDE desktop launcher installed successfully!"
echo " Location: $DESKTOP_FILE"
echo " You can now launch PyMint IDE from your Linux Mint menu."
echo "=========================================================="
