# PyMint IDE 🍃

**PyMint IDE** es un entorno de desarrollo integrado (IDE) de escritorio nativo, profesional y ultraligero diseñado específicamente para desarrollo Backend en Python (FastAPI, Django, Docker, PostgreSQL y NoSQL) y optimizado al extremo para hardware de bajos recursos (ej. Intel Celeron / 4GB RAM) bajo Linux Mint Cinnamon.

---

## 🚀 Características Clave

- **100% Nativo:** Desarrollado sobre `PyQt6` y `QScintilla` en C++. Cero Electron, Cero Chromium, Cero NodeJS.
- **Consumo de Memoria Ultrabajo:** Menos de 85 MB de RAM en uso normal.
- **Cero Bloqueo de UI (Non-blocking):** Todas las tareas pesadas (Jedi, Ruff, Git, UV, Terminal PTY) corren en hilos secundarios (`QThread`) o procesos asíncronos (`QProcess`).
- **Editor QScintilla Inteligente:**
  - Tema oscuro Catppuccin Mocha de bajo cansancio visual.
  - Autocompletado con `Jedi` y *debounce* de 350 ms para no saturar la CPU Celeron.
  - Detección y vinculación automática al `.venv` del proyecto.
  - Resaltado nativo para Python, SQL (PostgreSQL), JSON, YAML, Bash, Dockerfile y Markdown.
  - Linting y formateo instantáneo con `Ruff` (en Rust) al guardar (`Ctrl+S`) y (`Ctrl+Shift+F`).
- **Terminal Profesional Linux Nativa:**
  - Terminal multi-pestaña usando PTY (`pty.openpty`) y `QSocketNotifier`.
  - Autoactivación de `.venv` en cada pestaña.
  - Botones de lanzamiento rápido: `▶ Run FastAPI` y `▶ Run Django`.
  - Botón de parada `⏹ Stop Server` con señal real `SIGINT (Ctrl+C)`.
- **Panel Git & GitHub Visual:**
  - Cambio y creación de ramas (`checkout -b`).
  - Grafo ASCII de commits en vivo (`git log --graph`).
  - Staging / Unstaging con un clic y visor de diffs.
  - Botones de sincronización: `⬆ Push`, `⬇ Pull`, `🔄 Fetch`, `🔗 Clone`.
- **Integración con `uv` (Astral):**
  - Inicialización de proyecto y entorno en 1 clic.
  - Instalador de paquetes (`uv add` / `uv remove`).
  - Presets Backend: FastAPI, Django, PostgreSQL y NoSQL.
- **Panel RAM Guard:**
  - Monitor en tiempo real de RAM libre leyendo `/proc/meminfo` cada 3 segundos.
  - Alerta visual si la memoria libre baja de 450 MB.
  - Interruptores 1-clic para iniciar o detener `docker`, `postgresql`, `mongod` y `redis-server` (con polkit `pkexec` de Cinnamon).
  - Control de contenedores Docker y `docker compose up -d` / `down`.

---

## 📂 Estructura del Proyecto

```text
pymint_ide/
├── main.py                      # Punto de entrada y configuración de bajo consumo
├── pyproject.toml               # Configuración de dependencias gestionada con uv
├── install_desktop.sh           # Instalador de acceso directo en Linux Mint
├── assets/
│   └── pymint-icon.svg          # Ícono vectorial de PyMint IDE
├── core/
│   ├── config.py                # Rutas, paleta de colores y preferencias persistentes
│   ├── lsp_worker.py            # Hilo secundario Jedi para autocompletado y firmas
│   ├── linter_runner.py         # Ejecución asíncrona de Ruff (check & format)
│   ├── uv_manager.py            # Controlador asíncrono de comandos uv
│   ├── git_manager.py           # Controlador asíncrono de Git y GitHub
│   └── service_guard.py         # Monitor /proc/meminfo y gestor de servicios
└── ui/
    ├── main_window.py           # Ventana principal con QSplitter acoplables
    ├── file_tree.py             # Explorador filtrado sin indexación pesada
    ├── editor_tabs.py           # Gestor de pestañas e indicador de modificado (*)
    ├── code_editor.py           # Editor QsciScintilla con marcadores de Ruff
    ├── terminal_panel.py        # Terminal Linux multi-pestaña PTY
    ├── git_panel.py             # Panel visual de Git, ramas y GitHub
    ├── uv_dialog.py             # Panel de gestión uv y presets Backend
    └── service_panel.py         # Panel "RAM Guard" de servicios y Docker
```

---

## ⌨️ Atajos de Teclado

| Atajo | Acción |
|---|---|
| `Ctrl+S` | Guardar archivo actual y ejecutar linting Ruff |
| `Ctrl+Shift+S` | Guardar todos los archivos abiertos |
| `Ctrl+Shift+F` | Formatear archivo con Ruff |
| `Ctrl+Espacio` | Disparar autocompletado inteligente Jedi |
| `F11` | Alternar Pantalla Completa (Full Screen) |
| `Ctrl+B` | Mostrar / Ocultar barra lateral |
| `Ctrl+\`` | Mostrar / Ocultar panel de terminal |
| `Ctrl+C` (en Terminal) | Enviar señal de interrupción SIGINT al proceso |
| `Ctrl+L` (en Terminal) | Limpiar pantalla de terminal |
