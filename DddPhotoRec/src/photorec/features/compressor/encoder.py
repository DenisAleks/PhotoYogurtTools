from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageOps

#
# HEIC/HEIF support (needed to decode iPhone photos before re-encoding).
#
try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except Exception:
    pass


# JPEG qualities tried from best to floor when fitting a size budget.
QUALITY_STEPS: Tuple[int, ...] = (92, 88, 84, 80, 76, 72, 70)
QUALITY_FLOOR = QUALITY_STEPS[-1]

_ORIENTATION_TAG = 0x0112


def encode_jpeg_to_target(
    file: Path,
    target_bytes: int,
) -> Optional[Tuple[bytes, int, bool]]:
    """Re-encode an image to JPEG at the same resolution, aiming for <= target.

    Returns (jpeg_bytes, quality_used, fits_target), or None if the file can't
    be opened. Picks the highest quality whose output fits `target_bytes`; if
    even the floor quality is bigger, returns the floor result with
    `fits_target=False` — it never goes below the floor, so quality is
    protected. EXIF (date/GPS, with orientation baked into the pixels) and the
    ICC colour profile are preserved.
    """
    try:
        with Image.open(file) as raw:
            upright = ImageOps.exif_transpose(raw)

            exif = _exif_bytes(upright)
            icc = upright.info.get("icc_profile")
            image = _to_jpeg_mode(upright)

            fallback: Optional[bytes] = None

            for quality in QUALITY_STEPS:
                data = _encode(image, quality, exif, icc)

                if len(data) <= target_bytes:
                    return data, quality, True

                # Descending list, so the last one is the floor (smallest).
                fallback = data

            return fallback, QUALITY_FLOOR, False
    except Exception:
        return None


# ----------------------------------------------------------------------
# INTERNAL
# ----------------------------------------------------------------------

def _encode(image: Image.Image, quality: int, exif, icc) -> bytes:
    buffer = BytesIO()

    params = {
        "format": "JPEG",
        "quality": quality,
        "optimize": True,
        "progressive": True,
    }

    if exif:
        params["exif"] = exif
    if icc:
        params["icc_profile"] = icc

    image.save(buffer, **params)

    return buffer.getvalue()


_EXIF_IFD = 0x8769
_GPS_IFD = 0x8825


def _exif_bytes(image: Image.Image):
    try:
        exif = image.getexif()

        # Force-load the nested IFDs so they survive tobytes(): the capture
        # date (DateTimeOriginal) lives in the Exif IFD and GPS in the GPS IFD,
        # not in the base IFD.
        exif.get_ifd(_EXIF_IFD)
        exif.get_ifd(_GPS_IFD)

        # Pixels are already upright after exif_transpose, so drop the tag to
        # avoid a viewer rotating the image a second time.
        exif.pop(_ORIENTATION_TAG, None)

        data = exif.tobytes()
        return data or None
    except Exception:
        return None


def _to_jpeg_mode(image: Image.Image) -> Image.Image:
    # JPEG has no alpha channel — flatten transparency onto white.
    if image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    ):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[-1])
        return background

    if image.mode not in ("RGB", "L"):
        return image.convert("RGB")

    return image
