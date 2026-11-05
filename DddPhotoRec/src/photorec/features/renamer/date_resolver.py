import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from photorec.features.renamer.exif_reader import ExifReader
from photorec.shared.media_scanner import IMAGE_EXTENSIONS

#
# Date sources:
#   "exif"       - real capture time from image metadata (photos only)
#   "filename"   - a date embedded in the file name (IMG_20241005_143022, ...)
#   "filesystem" - creation/modification time (last resort, always available)
#
# EXIF normally wins, but a date in the file name that is EARLIER than the
# EXIF time is preferred: a re-saved / re-exported photo often carries an EXIF
# timestamp from that later save, while the original capture date survives in
# the name.
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
        exif_dt: Optional[datetime] = None

        if file.suffix.lower() in IMAGE_EXTENSIONS:
            exif_dt = self._exif.read_datetime(file)

        filename_dt, filename_has_time = self._from_filename(file.name)

        # Prefer the file-name date only when it predates the EXIF capture time.
        if exif_dt is not None and filename_dt is not None:
            if self._filename_predates_exif(
                filename_dt, filename_has_time, exif_dt
            ):
                return filename_dt, SOURCE_FILENAME
            return exif_dt, SOURCE_EXIF

        if exif_dt is not None:
            return exif_dt, SOURCE_EXIF

        if filename_dt is not None:
            return filename_dt, SOURCE_FILENAME

        return self._from_filesystem(file), SOURCE_FILESYSTEM

    # ------------------------------------------------------------------
    # INTERNAL
    # ------------------------------------------------------------------

    def _filename_predates_exif(
        self,
        filename_dt: datetime,
        filename_has_time: bool,
        exif_dt: datetime,
    ) -> bool:
        if filename_has_time:
            # Full date-time in the name: compare exactly.
            return filename_dt < exif_dt

        # Date-only name (midnight): compare by calendar day, so a same-day
        # name does not overwrite the EXIF time with 00:00:00.
        return filename_dt.date() < exif_dt.date()

    def _from_filename(self, name: str) -> Tuple[Optional[datetime], bool]:
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
                ), True
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
                ), False
            except ValueError:
                pass

        return None, False

    def _from_filesystem(self, file: Path) -> datetime:
        stat = file.stat()

        # st_birthtime exists on macOS/BSD; fall back to mtime elsewhere.
        timestamp = getattr(stat, "st_birthtime", None) or stat.st_mtime

        return datetime.fromtimestamp(timestamp)
