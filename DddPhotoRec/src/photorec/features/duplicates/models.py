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
        # Space that could be freed by removing the redundant copies.
        return self.size * len(self.duplicates)
