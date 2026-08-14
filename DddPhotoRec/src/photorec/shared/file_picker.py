import subprocess
import sys
from pathlib import Path


def select_folder() -> str | None:
    downloads = Path.home() / "Downloads"

    script = f"""
from tkinter import Tk, filedialog

root = Tk()
root.withdraw()

folder = filedialog.askdirectory(
    initialdir=r"{downloads}"
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

    return folder if folder else None