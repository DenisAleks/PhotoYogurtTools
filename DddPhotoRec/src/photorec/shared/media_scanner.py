from pathlib import Path

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".heic",
}

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".m4v",
    ".avi",
    ".mkv",
    ".3gp",
}

MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS


class MediaScanner:

    def __init__(self, folder: str) -> None:
        self._folder = Path(folder)

    def scan(self) -> list[Path]:
        files = []

        for file in self._folder.rglob("*"):

            if not file.is_file():
                continue

            if file.suffix.lower() not in MEDIA_EXTENSIONS:
                continue

            files.append(file)

        return files
