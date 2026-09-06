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

        self._log("Indexing library (image pixels + video bytes)...")

        index = OriginalIndex()
        await index.build(
            original_files,
            log=self._log,
            cancel_check=self._is_cancelled,
        )

        self._log(
            f"Indexed library signatures: {index.count}"
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
        unique_new = 0
        unique_same_size = 0

        for i, file in enumerate(
            recovered,
            start=1,
        ):
            if self._is_cancelled():
                self._log(
                    f"Cancelled at {i - 1}/{total}."
                )
                return

            result = finder.find_original(file)

            if result.original is None:
                # Same dimensions but no pixel match ⇒ likely a re-compressed
                # or edited version, not a genuinely new photo.
                if result.had_dimension_match:
                    unique_same_size += 1
                else:
                    unique_new += 1

                processor.process_unique(
                    recovered=file,
                    recovered_root=folder,
                )

            else:
                duplicates += 1

                processor.process_duplicate(
                    recovered=file,
                    original=result.original,
                )

            if i % 100 == 0 or i == total:
                self._log(
                    f"Progress: {i}/{total} "
                    f"({i / total * 100:.1f}%) | "
                    f"duplicates={duplicates}, "
                    f"recovered={unique_new + unique_same_size}"
                )

                # Give the event loop a chance to breathe.
                await asyncio.sleep(0)

        if self._is_cancelled():
            return

        self._log("")
        self._log("Folder finished")
        self._log(f"Duplicates (same image content)          : {duplicates}")
        self._log(f"Recovered - genuinely new                : {unique_new}")
        self._log(f"Recovered - same dimensions, diff pixels : {unique_same_size}")

        if unique_same_size > 0:
            self._log("")
            self._log(
                f"NOTE: {unique_same_size} 'recovered' file(s) share a library "
                "photo's dimensions but have different pixels — likely "
                "re-compressed or edited versions. Exact pixel matching keeps "
                "these as new (matching them would need fuzzy/perceptual "
                "matching)."
            )

    def _is_cancelled(self) -> bool:
        if self._cancel_check is None:
            return False

        return self._cancel_check()

    def _log(self, message: str) -> None:
        if self._log_callback is not None:
            self._log_callback(message)