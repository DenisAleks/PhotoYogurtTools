import asyncio
from pathlib import Path
from typing import Callable, Optional

from photorec.features.recovery.duplicate_finder import DuplicateFinder
from photorec.features.recovery.duplicate_processor import DuplicateProcessor
from photorec.features.recovery.original_index import OriginalIndex
from photorec.shared.media_scanner import MediaScanner


LogCallback = Callable[[str], None]
CancelCheck = Callable[[], bool]


class PhotoRecoveryService:
    def __init__(
        self,
        original_folder: str,
        recovered_folder: str,
        output_folder: str,
        move_files: bool = False,
        log: Optional[LogCallback] = None,
        cancel_check: Optional[CancelCheck] = None,
    ) -> None:
        self._original_folder = Path(original_folder)
        self._recovered_folder = Path(recovered_folder)
        self._output_folder = Path(output_folder)

        self._move_files = move_files

        self._log_callback = log
        self._cancel_check = cancel_check

    async def run(self) -> None:
        self._log(
            f"Mode: {'MOVE' if self._move_files else 'COPY'} files"
        )

        self._log("Scanning original folder...")

        scanner = MediaScanner(
            str(self._original_folder)
        )

        original_files = scanner.scan()

        self._log(
            f"Original files: {len(original_files)}"
        )

        if self._is_cancelled():
            self._log("Cancelled.")
            return

        self._log("Building hash index...")

        index = OriginalIndex()
        index.build(original_files)

        self._log(
            f"Indexed originals: {index.count}"
        )

        if self._is_cancelled():
            self._log("Cancelled.")
            return

        finder = DuplicateFinder(
            index,
            cancel_check=self._is_cancelled,
        )

        await self._process_recovered_folder(
            finder
        )

    async def _process_recovered_folder(
        self,
        finder: DuplicateFinder,
    ) -> None:
        if self._is_cancelled():
            self._log("Cancelled.")
            return

        folder = self._recovered_folder

        self._log("")
        self._log(
            f"Scanning recovered folder: {folder}"
        )

        scanner = MediaScanner(str(folder))
        recovered = scanner.scan()

        total = len(recovered)

        self._log(
            f"Files found: {total}"
        )

        if total == 0:
            self._log(
                "No image files found."
            )
            return

        processor = DuplicateProcessor(
            finder=finder,
            originals_root=self._original_folder,
            output_root=self._output_folder,
            move_files=self._move_files,
        )

        duplicates = 0
        unique = 0

        try:
            for i, file in enumerate(
                recovered,
                start=1,
            ):
                if self._is_cancelled():
                    self._log(
                        f"Cancelled at {i - 1}/{total}."
                    )
                    return

                original = finder.find_original(file)

                if original is None:
                    unique += 1

                    processor.process_unique(
                        recovered=file,
                        recovered_root=folder,
                    )

                else:
                    duplicates += 1

                    processor.process_duplicate(
                        recovered=file,
                        original=original,
                    )

                if i % 100 == 0 or i == total:
                    self._log(
                        f"Progress: {i}/{total} "
                        f"({i / total * 100:.1f}%) | "
                        f"duplicates={duplicates}, "
                        f"recovered={unique}"
                    )

                    # Give the event loop a chance to breathe.
                    await asyncio.sleep(0)

        finally:
            self._log("Something goes wrong.")

        if self._is_cancelled():
            return

        self._log("")
        self._log("Folder finished")
        self._log(
            f"Duplicates : {duplicates}"
        )
        self._log(
            f"Recovered  : {unique}"
        )

    def _is_cancelled(self) -> bool:
        if self._cancel_check is None:
            return False

        return self._cancel_check()

    def _log(self, message: str) -> None:
        if self._log_callback is not None:
            self._log_callback(message)