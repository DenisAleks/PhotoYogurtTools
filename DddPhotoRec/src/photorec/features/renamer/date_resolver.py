import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from photorec.features.renamer.exif_reader import ExifReader
from photorec.shared.media_scanner import IMAGE_EXTENSIONS

#
# Date sources, in priority order:
#   "exif"       - real capture time from image metadata (photos only)
#   "filename"   - a date embedded in the file name (IMG_20241005_143022, ...)
#   "filesystem" - creation/modification time (last resort, always available)
#
SOURCE_EXIF = "exif"
SOURCE_FILENAME = "filename"
SOURCE_FILESYSTEM = "filesystem"


_FILENAME_DATETIME = re.compile(
    r"(19|20)(\d{2})"           # year
    r"[-_.]?"
    r"(0[1-9]|1[0-2])"          # month
    r"[-_.]?"
    r"(0[1-9]|[12]\d|3[01])"    # day
    r"[-_.T ]?"
    r"([01]\d|2[0-3])"          # hour
    r"[-_.]?"
    r"([0-5]\d)"                # minute
    r"[-_.]?"
    r"([0-5]\d)"                # second
)

_FILENAME_DATE = re.compile(
    r"(19|20)(\d{2})"           # year
    r"[-_.]?"
    r"(0[1-9]|1[0-2])"          # month
    r"[-_.]?"
    r"(0[1-9]|[12]\d|3[01])"    # day
)


class DateResolver:
    """Resolves a capture date-time for a media file with a fallback chain."""

    def __init__(self) -> None:
        self._exif = ExifReader()

    def resolve(self, file: Path) -> Tuple[datetime, str]:
        if file.suffix.lower() in IMAGE_EXTENSIONS:
            exif_dt = self._exif.read_datetime(file)

            if exif_dt is not None:
                return exif_dt, SOURCE_EXIF

        filename_dt = self._from_filename(file.name)

        if filename_dt is not None:
            return filename_dt, SOURCE_FILENAME

        return self._from_filesystem(file), SOURCE_FILESYSTEM

    # ------------------------------------------------------------------
    # INTERNAL
    # ------------------------------------------------------------------

    def _from_filename(self, name: str) -> Optional[datetime]:
        match = _FILENAME_DATETIME.search(name)

        if match:
            year = int(match.group(1) + match.group(2))

            try:
                return datetime(
                    year,
                    int(match.group(3)),
                    int(match.group(4)),
                    int(match.group(5)),
                    int(match.group(6)),
                    int(match.group(7)),
                )
            except ValueError:
                pass

        match = _FILENAME_DATE.search(name)

        if match:
            year = int(match.group(1) + match.group(2))

            try:
                return datetime(
                    year,
                    int(match.group(3)),
                    int(match.group(4)),
                )
            except ValueError:
                pass

        return None

    def _from_filesystem(self, file: Path) -> datetime:
        stat = file.stat()

        # st_birthtime exists on macOS/BSD; fall back to mtime elsewhere.
        timestamp = getattr(stat, "st_birthtime", None) or stat.st_mtime

        return datetime.fromtimestamp(timestamp)
