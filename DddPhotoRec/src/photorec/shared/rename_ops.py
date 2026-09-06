import asyncio
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional


LogCallback = Callable[[str], None]
CancelCheck = Callable[[], bool]


@dataclass(slots=True)
class RenameOperation:
    """One file move. Undo replays these in reverse (target -> source).

    Used by any feature that renames/moves files (the Renamer, the Duplicates
    Finder) so they share one undo implementation.
    """
    source: Path
    target: Path


async def undo_operations(
    operations: List[RenameOperation],
    log: Optional[LogCallback] = None,
    cancel_check: Optional[CancelCheck] = None,
) -> int:
    """Reverses a batch of moves: puts every file back where it started."""

    def emit(message: str) -> None:
        if log is not None:
            log(message)

    total = len(operations)

    if total == 0:
        emit("Nothing to undo.")
        return 0

    emit(f"Undoing {total} file(s)...")

    restored = 0
    failed = 0

    for i, operation in enumerate(reversed(operations), start=1):
        if cancel_check is not None and cancel_check():
            emit(f"Undo cancelled at {i - 1}/{total}.")
            break

        if not operation.target.exists():
            failed += 1
            emit(f"Missing, skipped: {operation.target.name}")
        elif operation.source.exists():
            failed += 1
            emit(f"Original path occupied, skipped: {operation.source.name}")
        else:
            operation.source.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(operation.target), str(operation.source))
            restored += 1

            # Remove the folder we may have created, if it is now empty.
            try:
                operation.target.parent.rmdir()
            except OSError:
                pass

        if i % 50 == 0 or i == total:
            await asyncio.sleep(0)

    emit("")
    emit("Undo finished")
    emit(f"Restored : {restored}")
    emit(f"Skipped  : {failed}")

    return restored
