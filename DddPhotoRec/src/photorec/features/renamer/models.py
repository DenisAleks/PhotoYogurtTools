from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class RenameOperation:
    """One file move performed by a rename run.

    `source` is where the file was before the run; `target` is where it
    ended up. Undo replays these in reverse (target -> source).
    """
    source: Path
    target: Path
