from pathlib import Path

# Marker inserted into a duplicate's name, e.g. IMG_5678_dup_IMG_1234.jpg.
# Also used to detect already-flagged files so re-runs are idempotent.
DUP_MARKER = "_dup_"


def is_flagged(file: Path) -> bool:
    return DUP_MARKER in file.stem


def flagged_name(duplicate: Path, keeper: Path) -> str:
    """`{duplicate-stem}_dup_{keeper-stem}{ext}` (keeps the duplicate's ext)."""
    return f"{duplicate.stem}{DUP_MARKER}{keeper.stem}{duplicate.suffix}"
