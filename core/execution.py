"""Build commands as argument lists so paths never become shell input."""

import shlex
import shutil
from pathlib import Path

from core.config import settings


def command_for_file(filepath: str, project_dir: str) -> tuple[list[str], str]:
    path = Path(filepath).resolve()
    cwd = str(Path(project_dir).resolve())
    if path.suffix.lower() == ".py":
        python = (
            settings.get_venv_python(str(path.parent))
            or shutil.which("python3")
            or "python3"
        )
        return [python, "-u", str(path)], cwd
    if path.suffix.lower() in (".sh", ".bash"):
        return ["bash", str(path)], cwd
    if path.suffix.lower() == ".rs" or path.name.lower() == "cargo.toml":
        for directory in (path.parent, *path.parent.parents):
            if (directory / "Cargo.toml").is_file():
                return [settings.get_cargo_path(), "run", "--jobs", "1"], str(directory)
        # A private build directory avoids collisions between tabs or IDE instances.
        script = (
            "build_dir=$(mktemp -d) || exit 1; "
            "trap 'rm -rf -- \"$build_dir\"' EXIT; "
            f"{shlex.quote(settings.get_rustc_path())} {shlex.quote(str(path))} "
            '-o "$build_dir/program" && "$build_dir/program"'
        )
        return ["bash", "-c", script], cwd
    raise ValueError(
        f"No se puede ejecutar este tipo de archivo: {path.suffix or path.name}"
    )
