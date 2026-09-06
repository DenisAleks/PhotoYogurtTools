from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass(slots=True)
class DuplicateGroup:
    """A set of byte-identical files.

    `keeper` is left untouched (the oldest file); every path in `duplicates`
    is a redundant copy that will be flagged in place.
    """
    hash: str
    size: int
    keeper: Path
    duplicates: List[Path] = field(default_factory=list)

    @property
    def total_files(self) -> int:
        return len(self.duplicates) + 1

    @property
    def reclaimable_bytes(self) -> int:
        # Space freed by removing the redundant copies. Summed from each file's
        # actual size, since pixel-identical images can differ in byte size
        # (padding, EXIF) and so aren't necessarily `self.size` each.
        total = 0

        for duplicate in self.duplicates:
            try:
                total += duplicate.stat().st_size
            except OSError:
                continue

        return total
