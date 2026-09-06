import asyncio
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional, Set, Tuple

from photorec.features.duplicates.duplicate_scanner import DuplicateScanner
from photorec.features.duplicates.models import DuplicateGroup
from photorec.features.duplicates.naming import flagged_name, is_flagged
from photorec.features.duplicates.report_writer import ReportWriter
from photorec.shared.media_scanner import MediaScanner
from photorec.shared.rename_ops import RenameOperation


LogCallback = Callable[[str], None]
CancelCheck = Callable[[], bool]

# How many groups to print to the on-screen log (the .md report holds all).
_LOG_GROUP_CAP = 100


class DuplicatesService:
    """Scans an input folder for duplicates and (separately) flags them.

    `scan()` is read-only and writes the Markdown report. `rename()` is the
    explicit second step that renames duplicates in place.
    """

    def __init__(
        self,
        input_folder: str,
        log: Optional[LogCallback] = None,
        cancel_check: Optional[CancelCheck] = None,
    ) -> None:
        self._input_folder = Path(input_folder)
        self._log_callback = log
        self._cancel_check = cancel_check

    # ------------------------------------------------------------------
    # SCAN (read-only)
    # ------------------------------------------------------------------

    async def scan(self) -> Tuple[List[DuplicateGroup], Optional[Path]]:
        self._log(f"Scanning: {self._input_folder}")

        files = MediaScanner(str(self._input_folder)).scan()
        self._log(f"Media files found: {len(files)}")

        if not files:
            self._log("Nothing to scan.")
            return [], None

        scanner = DuplicateScanner(
            cancel_check=self._cancel_check,
            log=self._log,
        )

        groups = await scanner.scan(files)

        if self._is_cancelled():
            self._log("Cancelled.")
            return [], None

        self._log_summary(groups)
        self._log_groups(groups)

        report_path = self._write_report(groups, len(files))

        return groups, report_path

    # ------------------------------------------------------------------
    # RENAME (explicit second step)
    # ------------------------------------------------------------------

    async def rename(
        self,
        groups: List[DuplicateGroup],
    ) -> List[RenameOperation]:
        self._log("")
        self._log("Renaming duplicates in place...")

        operations: List[RenameOperation] = []
        planned: Set[Path] = set()

        renamed = 0
        skipped = 0

        total_groups = len(groups)

        for i, group in enumerate(groups, start=1):
            if self._is_cancelled():
                self._log(f"Cancelled at group {i - 1}/{total_groups}.")
                break

            for duplicate in group.duplicates:
                if is_flagged(duplicate):
                    skipped += 1
                    continue

                destination = duplicate.with_name(
                    flagged_name(duplicate, group.keeper)
                )

                destination = self._avoid_collision(destination, planned)

                if destination == duplicate:
                    skipped += 1
                    continue

                planned.add(destination)

                shutil.move(str(duplicate), str(destination))

                operations.append(
                    RenameOperation(
                        source=duplicate,
                        target=destination,
                    )
                )

                renamed += 1

            if i % 50 == 0 or i == total_groups:
                await asyncio.sleep(0)

        self._log("")
        self._log("Rename finished")
        self._log(f"Flagged : {renamed}")
        self._log(f"Skipped : {skipped}")

        return operations

    # ------------------------------------------------------------------
    # INTERNAL
    # ------------------------------------------------------------------

    def _write_report(
        self,
        groups: List[DuplicateGroup],
        files_scanned: int,
    ) -> Path:
        now = datetime.now()

        report_path = self._input_folder / (
            f"_DUPLICATES_REPORT_{now:%Y-%m-%d_%H%M}.md"
        )

        ReportWriter().write(
            report_path=report_path,
            input_folder=self._input_folder,
            groups=groups,
            files_scanned=files_scanned,
            when=now,
        )

        self._log("")
        self._log(f"Report written: {report_path.name}")

        return report_path

    def _log_summary(self, groups: List[DuplicateGroup]) -> None:
        redundant = sum(len(group.duplicates) for group in groups)
        reclaimable = sum(group.reclaimable_bytes for group in groups)

        self._log("")
        self._log("=" * 48)
        self._log(f"Duplicate groups : {len(groups)}")
        self._log(f"Redundant files  : {redundant}")
        self._log(f"Reclaimable      : {self._human(reclaimable)}")
        self._log("=" * 48)

    def _log_groups(self, groups: List[DuplicateGroup]) -> None:
        for index, group in enumerate(groups[:_LOG_GROUP_CAP], start=1):
            self._log("")
            self._log(
                f"[{index}] {group.total_files} copies · "
                f"{self._human(group.size)}"
            )
            self._log(f"    keep · {group.keeper.name}")

            for duplicate in group.duplicates:
                self._log(
                    f"    dup  · {duplicate.name}  ->  "
                    f"{flagged_name(duplicate, group.keeper)}"
                )

        hidden = len(groups) - _LOG_GROUP_CAP

        if hidden > 0:
            self._log("")
            self._log(f"...and {hidden} more group(s) — see the report.")

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

    def _human(self, size: int) -> str:
        value = float(size)

        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024 or unit == "TB":
                if unit == "B":
                    return f"{int(value)} {unit}"
                return f"{value:.1f} {unit}"
            value /= 1024

        return f"{size} B"

    def _is_cancelled(self) -> bool:
        return self._cancel_check is not None and self._cancel_check()

    def _log(self, message: str) -> None:
        if self._log_callback is not None:
            self._log_callback(message)
