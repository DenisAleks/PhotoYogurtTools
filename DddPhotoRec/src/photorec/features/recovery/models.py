from dataclasses import dataclass
from pathlib import Path

@dataclass(slots=True)
class FileInfo:
    path: Path
    size: int
    hash: str | None = None


@dataclass(slots=True)
class FindResult:
    original: Path | None
    recovered_hash: str | None