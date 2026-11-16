"""Compare rendering, e.g. python tests/benchmark_terminal.py --project /tmp/baseline.

A project is an extracted source snapshot with compatible dependencies. The test
feeds 2100 lines and times 200 subsequent updates with full scrollback. It measures
parser + document updates, not application startup or speed on another machine.
"""

import argparse
import json
import os
from pathlib import Path
import signal
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
args = parser.parse_args()
sys.path.insert(0, str(args.project.resolve()))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication
from ui.terminal_panel import PTYTerminalWidget

app = QApplication([])
app.setStyle("Fusion")
widget = PTYTerminalWidget()
pid = widget.pid
try:
    widget.resize(800, 240)
    widget.show()
    app.processEvents()
    widget.notifier.setEnabled(False)
    widget.stream.feed(b"line of representative command output\r\n" * 2100)
    widget._render_screen()
    app.processEvents()
    start = time.perf_counter()
    for index in range(200):
        widget.stream.feed(f"new output {index}\r\n".encode())
        widget._render_screen()
    elapsed = time.perf_counter() - start
    print(
        json.dumps(
            {
                "seconds": round(elapsed, 4),
                "updates": 200,
                "blocks": widget.document().blockCount(),
            }
        )
    )
finally:
    widget.close()
    if hasattr(widget, "_process"):
        widget._process.wait(timeout=2)
    else:
        # The original implementation did not reap its shell on close.
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        os.waitpid(pid, 0)
