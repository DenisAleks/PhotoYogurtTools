import asyncio
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional


LogCallback = Callable[[str], None]
CancelCheck = Callable[[], bool]
ProgressCallback = Callable[[int, int], None]


def _unlock(path: Path) -> None:
    """Clear a macOS 'locked' (immutable) flag so the file can be moved.

    No-op when there is nothing to clear or on systems without `os.chflags`.
    """
    if not hasattr(os, "chflags"):
        return
    try:
        flags = os.stat(path).st_flags
    except (OSError, AttributeError):
        return
    if not flags:
        return
    try:
        os.chflags(path, 0)
    except OSError:
        pass


def safe_move(source: Path, destination: Path) -> None:
    """Move a file, forcing past a macOS 'locked' (immutable) flag if present.

    A Finder-locked file (UF_IMMUTABLE) can't be renamed and raises EPERM
    ("Operation not permitted"). `os.replace` is used first — an atomic,
    same-filesystem rename that copies no metadata (so it never propagates the
    lock flag like `shutil.move`'s copy fallback does). On failure we clear the
    lock and retry; the moved file is left **unlocked**. A cross-filesystem move
    falls back to copy-then-delete.
    """
    try:
        os.replace(str(source), str(destination))
        return
    except OSError as first_error:
        _unlock(source)

        if destination.exists():
            _unlock(destination)

        try:
            os.replace(str(source), str(destination))
            return
        except OSError:
            pass

        # Different filesystem (EXDEV) or still blocked — copy then delete.
        try:
            shutil.copy2(str(source), str(destination))
        except OSError:
            raise first_error

        if hasattr(os, "chflags"):
            try:
                os.chflags(str(destination), 0)
            except OSError:
                pass

        try:
            os.unlink(str(source))
        except OSError:
            pass


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
    progress: Optional[ProgressCallback] = None,
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
            try:
                operation.source.parent.mkdir(parents=True, exist_ok=True)
                safe_move(operation.target, operation.source)
                restored += 1
            except OSError as error:
                failed += 1
                emit(f"Couldn't restore {operation.target.name}: {error}")
            else:
                # Remove the folder we may have created, if it is now empty.
                try:
                    operation.target.parent.rmdir()
                except OSError:
                    pass

        if progress is not None:
            progress(i, total)

        if i % 50 == 0 or i == total:
            await asyncio.sleep(0)

    emit("")
    emit("Undo finished")
    emit(f"Restored : {restored}")
    emit(f"Skipped  : {failed}")

    return restored
