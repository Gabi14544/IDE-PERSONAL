# PyMint IDE

IDE nativo para Python y Rust en Linux. La interfaz usa PyQt6 y QScintilla; la terminal usa PTY y pyte. El diseño compacto está pensado para pantallas de 1366×768 y equipos como el Celeron N2808 con 4 GB de RAM y Linux Mint 22.3.

## Interfaz y ejecución

- Tema **Graphite** con superficies neutras, acento azul, paneles ajustables y una pantalla inicial limpia. Los temas anteriores siguen disponibles en **Ajustes**, junto con la fuente y su tamaño.
- Un único botón **Ejecutar** guarda el archivo activo y lo abre en una pestaña de ejecución independiente. Las terminales de trabajo conservan sus comandos y su directorio.
- Python usa el intérprete de la `.venv` más cercana al archivo y salida sin búfer. También se pueden ejecutar scripts Bash, proyectos Cargo y archivos Rust sueltos. Rust requiere `cargo`/`rustc`; las compilaciones Cargo se limitan a un trabajo.
- La pestaña de ejecución muestra el código de salida y se reutiliza en la siguiente ejecución. Si ya hay un programa activo, primero hay que detenerlo.
- El cierre del IDE permite guardar, descartar o cancelar cuando quedan cambios pendientes.

## Terminal y rendimiento

La terminal procesa entrada y salida sin bloquear, conserva las secuencias UTF-8 y ANSI entre lecturas y muestra colores, negrita, cursiva y subrayado. El historial está limitado a 2000 líneas por sesión. Las actualizaciones se agrupan cada 33 ms y solo se reemplaza el texto que cambió; el historial antiguo se elimina de forma incremental. La selección y la posición de lectura se mantienen mientras llega salida nueva.

Los procesos reciben el tamaño real de la terminal y `Ctrl+C` interrumpe el trabajo en primer plano. Los procesos terminados se recogen para evitar shells zombis. El menú contextual y `Ctrl+Shift+C` / `Ctrl+Shift+V` permiten copiar y pegar.

Jedi se carga en segundo plano al solicitar el primer autocompletado. El explorador evita iconos personalizados de carpetas y usa filas de altura uniforme. Git se consulta al abrir su panel y los servicios del sistema al abrir su menú; no se lanzan esas consultas al iniciar el IDE. La interfaz no usa animaciones ni efectos de composición.

En una medición del entorno de desarrollo, 200 actualizaciones con historial lleno pasaron de **3,63 s a 0,37 s** frente a la implementación anterior. Es una medición del renderizado de terminal, no una promesa de aceleración de toda la aplicación ni una prueba en la notebook física. Se puede repetir con `tests/benchmark_terminal.py` usando el mismo intérprete para ambas versiones.

## Instalación y arranque

Requiere Linux y Python 3.10 o superior. En Linux Mint 22.3 se puede usar Python 3.12. Con [uv](https://docs.astral.sh/uv/):

```bash
cd IDE-PERSONAL
uv venv .venv
uv pip install --python .venv/bin/python -r pyproject.toml --extra wheels ruff uv
source .venv/bin/activate
python main.py /ruta/a/tu/proyecto
```

La instalación lee las dependencias del manifiesto y ejecuta el proyecto desde su código fuente. No es necesario iniciar Docker, PostgreSQL, MongoDB o Redis para usar el IDE. El control opcional de servicios requiere systemd y polkit en el sistema local.

## Atajos

| Acción | Atajo |
| --- | --- |
| Ejecutar archivo activo | F5 / Ctrl+R |
| Detener ejecución | Shift+F5 |
| Interrumpir trabajo en terminal | Ctrl+C |
| Abrir carpeta | Ctrl+O |
| Guardar / guardar todo | Ctrl+S / Ctrl+Shift+S |
| Formatear con Ruff | Ctrl+Shift+F |
| Autocompletado | Ctrl+Espacio |
| Mostrar panel lateral | Ctrl+B |
| Mostrar terminal | Ctrl+J / Ctrl+` |
| Pantalla completa | F11 |
| Copiar / pegar en terminal | Ctrl+Shift+C / Ctrl+Shift+V |
| Desplazar historial de terminal | Shift+PageUp / Shift+PageDown |

## Validación

```bash
source .venv/bin/activate
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v
python tests/benchmark_terminal.py
```

Las pruebas funcionales cubren ejecución y guardado, rutas con caracteres especiales, selección del intérprete, bloqueo de ejecuciones simultáneas, cierre con cambios pendientes, tamaños de ventana reducidos, autocompletado Jedi y terminal real: entrada, salida abundante, colores ANSI, secuencias partidas, redimensionado, interrupción, historial y recogida de procesos.

El modo `offscreen` permite validar sin un escritorio. La apariencia y el rendimiento final deben comprobarse también en el equipo físico. La terminal implementa el subconjunto VT soportado por pyte; no pretende sustituir todas las funciones de un emulador de terminal dedicado.
