from hashlib import sha256
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image

#
# HEIC support (iPhone photos). Optional: if pillow-heif is missing, HEIC
# files just fail to decode and fall through as "unique".
#
try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except Exception:
    pass

from photorec.shared.media_scanner import IMAGE_EXTENSIONS


Dimensions = Tuple[int, int, str]


def is_image(file: Path) -> bool:
    return file.suffix.lower() in IMAGE_EXTENSIONS


def image_signature(
    file: Path,
) -> Tuple[Optional[Dimensions], Optional[str]]:
    """Return ((width, height, mode), pixel-hash) for an image.

    The hash is SHA-256 of the *decoded pixel data*, so it ignores the file
    container, trailing padding, and EXIF metadata — two files with identical
    pixels hash the same even if their raw bytes differ (exactly the case for
    recovered photos vs their library copies). Returns (None, None) if the file
    can't be read as an image.
    """
    try:
        with Image.open(file) as image:
            dimensions: Dimensions = (
                image.width,
                image.height,
                image.mode,
            )

            image.load()

            hasher = sha256()
            hasher.update(
                f"{dimensions[0]}x{dimensions[1]}:{dimensions[2]}".encode()
            )
            hasher.update(image.tobytes())

            return dimensions, hasher.hexdigest()
    except Exception:
        return None, None
