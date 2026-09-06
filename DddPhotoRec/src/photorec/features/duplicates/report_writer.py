from datetime import datetime
from pathlib import Path
from typing import List

from photorec.features.duplicates.models import DuplicateGroup
from photorec.features.duplicates.naming import flagged_name


class ReportWriter:
    """Writes a human-readable Markdown report of the duplicate groups."""

    def write(
        self,
        report_path: Path,
        input_folder: Path,
        groups: List[DuplicateGroup],
        files_scanned: int,
        when: datetime,
    ) -> Path:
        redundant = sum(len(group.duplicates) for group in groups)
        reclaimable = sum(group.reclaimable_bytes for group in groups)

        lines: List[str] = [
            "# Duplicate files report",
            "",
            f"- **Scanned:** `{input_folder}`",
            f"- **Date:** {when:%Y-%m-%d %H:%M}",
            f"- **Files scanned:** {files_scanned:,}",
            f"- **Duplicate groups:** {len(groups):,}",
            f"- **Redundant files:** {redundant:,}",
            f"- **Reclaimable space:** {self._human(reclaimable)}",
            "",
            "> The keeper (oldest file) is left untouched. Each duplicate is "
            "renamed in place; nothing is deleted. Delete by hand after review.",
            "",
            "---",
            "",
        ]

        if not groups:
            lines.append("No duplicates found. 🎉")
            report_path.write_text("\n".join(lines), encoding="utf-8")
            return report_path

        for index, group in enumerate(groups, start=1):
            lines.extend(
                self._group_lines(index, group, input_folder)
            )

        report_path.write_text("\n".join(lines), encoding="utf-8")

        return report_path

    # ------------------------------------------------------------------
    # INTERNAL
    # ------------------------------------------------------------------

    def _group_lines(
        self,
        index: int,
        group: DuplicateGroup,
        input_folder: Path,
    ) -> List[str]:
        lines = [
            f"## Group {index} — {group.total_files} copies · "
            f"{self._human(group.size)} · sha256 `{group.hash[:12]}…`",
            "",
            f"- ✅ keep · `{self._relative(group.keeper, input_folder)}`",
        ]

        for duplicate in group.duplicates:
            lines.append(
                f"- 🔁 dup  · `{self._relative(duplicate, input_folder)}`"
                f"  →  `{flagged_name(duplicate, group.keeper)}`"
            )

        lines.append("")

        return lines

    def _relative(self, file: Path, root: Path) -> str:
        try:
            return str(file.relative_to(root))
        except ValueError:
            return str(file)

    def _human(self, size: int) -> str:
        value = float(size)

        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024 or unit == "TB":
                if unit == "B":
                    return f"{int(value)} {unit}"
                return f"{value:.1f} {unit}"
            value /= 1024

        return f"{size} B"
