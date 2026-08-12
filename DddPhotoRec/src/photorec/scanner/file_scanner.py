from pathlib import Path
from collections import Counter


IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".heic",
}

class ImageScanner:
    def __init__(self, folder: str) -> None:
        self._folder = Path(folder)

    def scan(self) -> list[Path]:
        files = []

        for file in self._folder.rglob("*"):
            if not file.is_file():
                continue

            if file.suffix.lower() in IMAGE_EXTENSIONS:
                files.append(file)

        return files