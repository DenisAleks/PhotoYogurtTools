from csv import DictWriter
from pathlib import Path
import shutil

from photorec.features.recovery.duplicate_finder import DuplicateFinder


class DuplicateProcessor:

    def __init__(
        self,
        finder: DuplicateFinder,
        originals_root: Path,
        output_root: Path,
        move_files: bool = False,  # toggled from the UI; copy is the safe default
    ) -> None:

        self._move_files = move_files
        self._finder = finder
        self._originals_root = originals_root

        self._duplicates_root = output_root / "duplicates"
        self._recovered_root = output_root / "recovered"

        self._duplicates_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._recovered_root.mkdir(
            parents=True,
            exist_ok=True,
        )

    def process_duplicate(
        self,
        recovered: Path,
        original: Path,
    ) -> None:

        relative = original.relative_to(
            self._originals_root
        )

        destination = (
            self._duplicates_root /
            relative.parent /
            f"{original.stem}_DUP{recovered.suffix.lower()}"
        )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._transfer(
            recovered,
            destination,
        )

    def _transfer(self, source: Path, destination: Path):

        if self._move_files:
            shutil.move(source, destination)
        else:
            shutil.copy2(source, destination)

    def process_unique(
        self,
        recovered: Path,
        recovered_root: Path,
    ) -> None:

        relative = recovered.relative_to(
            recovered_root
        )

        destination = (
            self._recovered_root /
            recovered_root.name /
            relative
        )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._transfer(
            recovered,
            destination,
        )
