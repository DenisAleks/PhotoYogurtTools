import asyncio
import shutil
from pathlib import Path
from typing import Callable, List, Optional, Set

from photorec.features.renamer.date_resolver import DateResolver
from photorec.features.renamer.geocoder import Geocoder
from photorec.features.renamer.models import RenameOperation
from photorec.features.renamer.name_builder import NameBuilder
from photorec.shared.media_scanner import MediaScanner


LogCallback = Callable[[str], None]
CancelCheck = Callable[[], bool]


class RenamerService:
    """Renames + sorts media files in place, into pattern-driven subfolders.

    Files are moved within `input_folder` (e.g. into ``2024/10/...``). Every
    move is recorded as a `RenameOperation` and returned so the caller can
    offer Undo.
    """

    def __init__(
        self,
        input_folder: str,
        pattern: str,
        log: Optional[LogCallback] = None,
        cancel_check: Optional[CancelCheck] = None,
    ) -> None:
        self._input_folder = Path(input_folder)
        self._pattern = pattern

        self._log_callback = log
        self._cancel_check = cancel_check

        self._resolver = DateResolver()
        self._builder = NameBuilder()

        self._use_location = "{loc}" in pattern
        self._geocoder = Geocoder() if self._use_location else None

    async def run(self) -> List[RenameOperation]:
        self._log(f"Scanning: {self._input_folder}")

        files = MediaScanner(str(self._input_folder)).scan()
        total = len(files)

        self._log(f"Files found: {total}")

        if total == 0:
            self._log("Nothing to rename.")
            return []

        if self._use_location:
            if self._geocoder and self._geocoder.available:
                self._log("Location: reading GPS + offline geocoding.")
            else:
                self._log(
                    "Location: '{loc}' used but geocoding is unavailable; "
                    "install 'reverse-geocode'. Place will be blank."
                )

        operations: List[RenameOperation] = []
        planned: Set[Path] = set()

        renamed = 0
        skipped = 0

        for i, file in enumerate(files, start=1):
            if self._is_cancelled():
                self._log(f"Cancelled at {i - 1}/{total}.")
                break

            destination = self._plan_destination(file, planned)

            if destination is None:
                skipped += 1
            else:
                planned.add(destination)

                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(file), str(destination))

                operations.append(
                    RenameOperation(source=file, target=destination)
                )

                renamed += 1

            if i % 50 == 0 or i == total:
                self._log(
                    f"Progress: {i}/{total} "
                    f"({i / total * 100:.1f}%) | "
                    f"renamed={renamed}, skipped={skipped}"
                )

                await asyncio.sleep(0)

        self._log("")
        self._log("Rename finished")
        self._log(f"Renamed : {renamed}")
        self._log(f"Skipped : {skipped}")

        return operations

    # ------------------------------------------------------------------
    # INTERNAL
    # ------------------------------------------------------------------

    def _plan_destination(
        self,
        file: Path,
        planned: Set[Path],
    ) -> Optional[Path]:
        date, _ = self._resolver.resolve(file)

        place = (
            self._geocoder.place_for(file)
            if self._geocoder is not None
            else None
        )

        relative = self._builder.build(
            pattern=self._pattern,
            date=date,
            original_stem=file.stem,
            extension=file.suffix,
            place=place,
        )

        destination = self._input_folder / relative

        # Already where it should be - leave it alone.
        if destination == file:
            return None

        return self._avoid_collision(destination, planned)

    def _avoid_collision(
        self,
        destination: Path,
        planned: Set[Path],
    ) -> Path:
        if destination not in planned and not destination.exists():
            return destination

        stem = destination.stem
        suffix = destination.suffix
        parent = destination.parent

        counter = 1

        while True:
            candidate = parent / f"{stem}_{counter}{suffix}"

            if candidate not in planned and not candidate.exists():
                return candidate

            counter += 1

    def _is_cancelled(self) -> bool:
        if self._cancel_check is None:
            return False

        return self._cancel_check()

    def _log(self, message: str) -> None:
        if self._log_callback is not None:
            self._log_callback(message)


async def undo_operations(
    operations: List[RenameOperation],
    log: Optional[LogCallback] = None,
    cancel_check: Optional[CancelCheck] = None,
) -> int:
    """Reverses a rename run: moves every file back to its original path."""

    def emit(message: str) -> None:
        if log is not None:
            log(message)

    total = len(operations)

    if total == 0:
        emit("Nothing to undo.")
        return 0

    emit(f"Undoing {total} moved file(s)...")

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

            # Remove the now-empty dated folder if we can.
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
