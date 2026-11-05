import asyncio
from pathlib import Path
from typing import Callable, List, Optional, Set

from photorec.features.renamer.date_resolver import DateResolver
from photorec.features.renamer.geocoder import Geocoder
from photorec.features.renamer.name_builder import NameBuilder
from photorec.shared.image_signature import is_image
from photorec.shared.media_scanner import MediaScanner
from photorec.shared.rename_ops import (
    RenameOperation,
    safe_move,
    undo_operations,
)
from photorec.shared.screenshot_detector import is_screenshot


LogCallback = Callable[[str], None]
CancelCheck = Callable[[], bool]
ProgressCallback = Callable[[int, int], None]

# Folder (inside the input folder) that extracted screenshots are moved into.
SCREENSHOTS_FOLDER_NAME = "_Screenshots"


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
        progress: Optional[ProgressCallback] = None,
    ) -> None:
        self._input_folder = Path(input_folder)
        self._pattern = pattern

        self._log_callback = log
        self._cancel_check = cancel_check
        self._progress = progress

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
        failed = 0

        for i, file in enumerate(files, start=1):
            if self._is_cancelled():
                self._log(f"Cancelled at {i - 1}/{total}.")
                break

            destination = self._plan_destination(file, planned)

            if destination is None:
                skipped += 1
            else:
                planned.add(destination)

                try:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    safe_move(file, destination)
                except OSError as error:
                    # A locked / permission-protected file must not stop the run.
                    failed += 1
                    planned.discard(destination)
                    self._log(f"   SKIPPED (locked/permission): {file} — {error}")
                else:
                    operations.append(
                        RenameOperation(source=file, target=destination)
                    )
                    renamed += 1

            self._report(i, total)

            if i % 50 == 0 or i == total:
                self._log(
                    f"Progress: {i}/{total} "
                    f"({i / total * 100:.1f}%) | "
                    f"renamed={renamed}, skipped={skipped}, failed={failed}"
                )

                await asyncio.sleep(0)

        self._log("")
        self._log("Rename finished")
        self._log(f"Renamed : {renamed}")
        self._log(f"Skipped : {skipped}")
        if failed:
            self._log(f"Failed  : {failed}  (could not move — see log)")

        return operations

    # ------------------------------------------------------------------
    # EXTRACT SCREENSHOTS (does not rename anything)
    # ------------------------------------------------------------------

    async def extract_screenshots(self) -> List[RenameOperation]:
        """Move detected screenshots into `_Screenshots/`; touch nothing else.

        Every image under the input folder is checked; photos are left exactly
        where they are (no renaming, no re-sorting). Returns the moves for Undo.
        """
        screenshots_root = self._input_folder / SCREENSHOTS_FOLDER_NAME

        self._log(f"Scanning for screenshots: {self._input_folder}")

        files = MediaScanner(str(self._input_folder)).scan()
        images = [
            f
            for f in files
            if is_image(f) and screenshots_root not in f.parents
        ]

        total = len(images)
        self._log(f"Image files to check: {total}")

        if total == 0:
            self._log("No images found.")
            return []

        operations: List[RenameOperation] = []
        planned: Set[Path] = set()

        moved = 0
        failed = 0

        for i, file in enumerate(images, start=1):
            if self._is_cancelled():
                self._log(f"Cancelled at {i - 1}/{total}.")
                break

            if is_screenshot(file):
                relative = file.relative_to(self._input_folder)
                destination = self._avoid_collision(
                    screenshots_root / relative,
                    planned,
                )
                planned.add(destination)

                try:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    safe_move(file, destination)
                except OSError as error:
                    failed += 1
                    planned.discard(destination)
                    self._log(f"   SKIPPED (locked/permission): {file} — {error}")
                else:
                    operations.append(
                        RenameOperation(source=file, target=destination)
                    )
                    moved += 1
                    self._log(f"   screenshot: {relative}")

            self._report(i, total)

            if i % 50 == 0 or i == total:
                self._log(f"Progress: {i}/{total} | screenshots={moved}")
                await asyncio.sleep(0)

        self._log("")
        self._log("Screenshot extraction finished")
        self._log(f"Screenshots moved : {moved}  (into {SCREENSHOTS_FOLDER_NAME}/)")
        self._log(f"Photos untouched  : {total - moved}")
        if failed:
            self._log(f"Failed            : {failed}  (could not move — see log)")

        return operations

    # ------------------------------------------------------------------
    # FLATTEN (does not rename anything)
    # ------------------------------------------------------------------

    async def flatten(self) -> List[RenameOperation]:
        """Move every media file from nested subfolders into the input root.

        Nothing is renamed — files keep their names. Files already in the root
        are left alone, and empty folders are NOT deleted. Returns the moves
        for Undo.
        """
        self._log(f"Flattening into: {self._input_folder}")

        files = MediaScanner(str(self._input_folder)).scan()
        # Only files that live below the root need moving.
        nested = [f for f in files if f.parent != self._input_folder]

        total = len(nested)
        self._log(f"Files to move: {total}  (already in root: {len(files) - total})")

        if total == 0:
            self._log("Nothing to flatten.")
            return []

        operations: List[RenameOperation] = []
        planned: Set[Path] = set()

        moved = 0
        failed = 0

        for i, file in enumerate(nested, start=1):
            if self._is_cancelled():
                self._log(f"Cancelled at {i - 1}/{total}.")
                break

            destination = self._avoid_collision(
                self._input_folder / file.name,
                planned,
            )
            planned.add(destination)

            try:
                safe_move(file, destination)
            except OSError as error:
                failed += 1
                planned.discard(destination)
                self._log(f"   SKIPPED (locked/permission): {file} — {error}")
            else:
                operations.append(
                    RenameOperation(source=file, target=destination)
                )
                moved += 1

            self._report(i, total)

            if i % 50 == 0 or i == total:
                self._log(f"Progress: {i}/{total} | moved={moved}")
                await asyncio.sleep(0)

        self._log("")
        self._log("Flatten finished")
        self._log(f"Moved   : {moved}  (into the input folder)")
        self._log("Empty folders were left in place.")
        if failed:
            self._log(f"Failed  : {failed}  (could not move — see log)")

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

    def _report(self, done: int, total: int) -> None:
        if self._progress is not None:
            self._progress(done, total)

    def _is_cancelled(self) -> bool:
        if self._cancel_check is None:
            return False

        return self._cancel_check()

    def _log(self, message: str) -> None:
        if self._log_callback is not None:
            self._log_callback(message)
