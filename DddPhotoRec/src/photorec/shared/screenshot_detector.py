from pathlib import Path

from PIL import Image, ExifTags

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except Exception:
    pass


# Tags a real camera photo carries and a screenshot does not.
_BASE_CAMERA_TAGS = (ExifTags.Base.Make, ExifTags.Base.Model)
_EXIF_CAMERA_TAGS = (
    ExifTags.Base.FNumber,
    ExifTags.Base.ExposureTime,
    ExifTags.Base.ISOSpeedRatings,
    ExifTags.Base.FocalLength,
    ExifTags.Base.LensModel,
    ExifTags.Base.DateTimeOriginal,
)

_SAMPLE = 150          # longest edge of the analysis thumbnail
_TOP_COLORS = 10
# A screenshot's few dominant colours (UI backgrounds) cover a large share of
# the image; a photo's most-common colours never do. Kept clear of a grayscale
# photo's spread so B&W photos aren't misflagged.
_TOP_RATIO_FLAT = 0.35


def is_screenshot(file: Path) -> bool:
    """True if an image looks like a screenshot rather than a camera photo.

    Two signals, both required, so a real photo is never flagged:
    1. **No camera EXIF** — photos have make/model/exposure; screenshots don't.
       (Camera EXIF survives this app's compression, so photos keep it.)
    2. **Flat, few-colour look** — UI backgrounds make a small set of colours
       cover most of the image, which a photo's detail never does.

    Filenames are not used at all. Returns False for anything unreadable.
    """
    try:
        with Image.open(file) as image:
            if _has_camera_exif(image):
                return False
            return _looks_flat(image)
    except Exception:
        return False


# ----------------------------------------------------------------------
# INTERNAL
# ----------------------------------------------------------------------

def _has_camera_exif(image: Image.Image) -> bool:
    try:
        exif = image.getexif()

        if any(exif.get(tag) for tag in _BASE_CAMERA_TAGS):
            return True

        sub = exif.get_ifd(ExifTags.IFD.Exif)
        return any(sub.get(tag) for tag in _EXIF_CAMERA_TAGS)
    except Exception:
        return False


def _looks_flat(image: Image.Image) -> bool:
    im = image.convert("RGB")

    width, height = im.size
    scale = max(width, height) / _SAMPLE

    if scale > 1:
        im = im.resize(
            (max(1, int(width / scale)), max(1, int(height / scale))),
            # NEAREST keeps flat regions flat (no edge blending).
            Image.NEAREST,
        )

    # Light quantization collapses JPEG noise inside flat areas.
    im = im.point(lambda v: v & 0xF8)

    total = im.width * im.height
    colors = im.getcolors(maxcolors=total)

    if not colors:
        return False

    colors.sort(reverse=True)
    top = sum(count for count, _ in colors[:_TOP_COLORS])

    return (top / total) > _TOP_RATIO_FLAT
