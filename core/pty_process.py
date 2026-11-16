"""Single-threaded exec trampoline for a controlling PTY.

Run as a script in a fresh subprocess, never via preexec_fn inside the Qt process.
The parent already creates a new session and attaches descriptors 0, 1 and 2.
"""

import fcntl
import os
import sys
import termios


def main():
    try:
        fcntl.ioctl(0, termios.TIOCSCTTY, 0)
        os.execvpe(sys.argv[1], sys.argv[1:], os.environ)
    except OSError as error:
        print(f"No se pudo iniciar {sys.argv[1]}: {error}", file=sys.stderr, flush=True)
        return 127


if __name__ == "__main__":
    sys.exit(main())
