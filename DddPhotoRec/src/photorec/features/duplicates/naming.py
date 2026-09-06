from pathlib import Path

# Prefix added to a flagged duplicate, e.g. DUP_IMG_5678.jpg.
# A prefix (not an infix) stays visible in Finder/Explorer, which truncate long
# names in the middle. Also used to detect already-flagged files so re-runs are
# idempotent.
DUP_PREFIX = "DUP_"

# Folder (under the input folder) that collects moved duplicates, mirroring the
# original subfolder structure.
DUP_FOLDER_NAME = "DUP"


def is_flagged(file: Path) -> bool:
    return file.stem.startswith(DUP_PREFIX)


def flagged_name(duplicate: Path) -> str:
    """`DUP_<original filename>` — visible prefix; keeper mapping is in the report."""
    return f"{DUP_PREFIX}{duplicate.name}"
