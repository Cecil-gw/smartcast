import shutil
import subprocess
import os
import sys
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def application_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def writable_data_dir() -> Path:
    base = application_dir()
    try:
        probe = base / ".smartcast-write-test"
        probe.write_text("", encoding="utf-8")
        probe.unlink()
        return base
    except OSError:
        fallback = Path(os.environ.get("APPDATA", str(Path.home()))) / "SmartCast"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", application_dir()))
    return base / relative


def resolve_tool(configured: str, embedded_dir: str, name: str) -> str:
    if configured:
        return configured
    embedded = resource_path(embedded_dir) / (name + ".exe")
    if embedded.exists():
        return str(embedded)
    found = shutil.which(name)
    return found or str(embedded)


def run_command(command: list[str], timeout: float = 5.0) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return completed.returncode, completed.stdout, completed.stderr
    except FileNotFoundError:
        return 127, "", "Executable not found"
    except subprocess.TimeoutExpired:
        return 124, "", "Command timed out"
