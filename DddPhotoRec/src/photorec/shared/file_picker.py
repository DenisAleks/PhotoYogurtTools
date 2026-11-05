import subprocess
import sys
from pathlib import Path

# Remembers the last folder the user picked, so the dialog reopens there
# next time (across app restarts). Falls back to Downloads on first run.
_STATE_FILE = Path.home() / ".dddphotorec" / "last_folder.txt"


def _read_last_folder() -> Path | None:
    try:
        stored = _STATE_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return None

    folder = Path(stored)
    return folder if stored and folder.is_dir() else None


def _write_last_folder(folder: str) -> None:
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _STATE_FILE.write_text(folder, encoding="utf-8")
    except OSError:
        pass


def select_folder() -> str | None:
    initial_dir = _read_last_folder() or (Path.home() / "Downloads")

    script = f"""
from tkinter import Tk, filedialog

root = Tk()
root.withdraw()

folder = filedialog.askdirectory(
    initialdir=r"{initial_dir}"
)

print(folder)

root.destroy()
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
    )

    folder = result.stdout.strip()

    if not folder:
        return None

    _write_last_folder(folder)

    return folder
