from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ExifTags

#
# HEIC support is optional. iPhones shoot HEIC by default, so we register
# the pillow-heif opener when it is installed; otherwise HEIC files simply
# fall back to filename / filesystem dates and carry no GPS.
#
try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
    HEIF_AVAILABLE = True
except Exception:
    HEIF_AVAILABLE = False


class ExifReader:
    """Reads capture date-time and GPS coordinates from image EXIF."""

    _DATE_FORMATS = (
        "%Y:%m:%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    )

    def read_datetime(self, file: Path) -> Optional[datetime]:
        raw = self._read_datetime_tag(file)

        if not raw:
            return None

        for fmt in self._DATE_FORMATS:
            try:
                return datetime.strptime(str(raw).strip(), fmt)
            except ValueError:
                continue

        return None

    def read_gps(self, file: Path) -> Optional[Tuple[float, float]]:
        gps = self._read_gps_tags(file)

        if not gps:
            return None

        try:
            latitude = self._to_degrees(gps[2], gps[1])
            longitude = self._to_degrees(gps[4], gps[3])
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            return None

        return latitude, longitude

    # ------------------------------------------------------------------
    # INTERNAL
    # ------------------------------------------------------------------

    def _read_datetime_tag(self, file: Path):
        try:
            with Image.open(file) as image:
                exif = image.getexif()

                if not exif:
                    return None

                exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)

                return (
                    exif_ifd.get(ExifTags.Base.DateTimeOriginal)
                    or exif_ifd.get(ExifTags.Base.DateTimeDigitized)
                    or exif.get(ExifTags.Base.DateTime)
                )
        except Exception:
            return None

    def _read_gps_tags(self, file: Path):
        try:
            with Image.open(file) as image:
                exif = image.getexif()

                if not exif:
                    return None

                return exif.get_ifd(ExifTags.IFD.GPSInfo)
        except Exception:
            return None

    def _to_degrees(self, value, ref) -> float:
        degrees, minutes, seconds = value

        result = (
            float(degrees)
            + float(minutes) / 60.0
            + float(seconds) / 3600.0
        )

        if str(ref).upper() in ("S", "W"):
            result = -result

        return result
