import asyncio
from collections import defaultdict
from pathlib import Path
from typing import Callable, Dict, List, Optional

from photorec.features.duplicates.models import DuplicateGroup
from photorec.shared.hash_calculator import HashCalculator


CancelCheck = Callable[[], bool]
LogCallback = Callable[[str], None]


class DuplicateScanner:
    """Finds byte-identical files via a size -> quick-hash -> full-hash funnel.

    Each stage only reads files that survived the previous one, so unique files
    are never fully read - important for large libraries.
    """

    def __init__(
        self,
        cancel_check: Optional[CancelCheck] = None,
        log: Optional[LogCallback] = None,
    ) -> None:
        self._cancel_check = cancel_check
        self._log = log or (lambda _msg: None)
        self._hash = HashCalculator()

    async def scan(self, files: List[Path]) -> List[DuplicateGroup]:
        by_size = self._group_by_size(files)

        size_candidates = self._collision_candidates(by_size)
        self._log(
            f"Same-size candidates: {len(size_candidates)} "
            f"(of {len(files)} files)"
        )

        if not size_candidates:
            return []

        by_quick = await self._group_by_quick_hash(size_candidates)

        quick_candidates = self._collision_candidates(by_quick)
        self._log(
            f"Quick-hash candidates: {len(quick_candidates)}"
        )

        if not quick_candidates:
            return []

        by_full = await self._group_by_full_hash(quick_candidates)

        return self._build_groups(by_full)

    # ------------------------------------------------------------------
    # STAGES
    # ------------------------------------------------------------------

    def _group_by_size(self, files: List[Path]) -> Dict[int, List[Path]]:
        buckets: Dict[int, List[Path]] = defaultdict(list)

        for file in files:
            try:
                buckets[file.stat().st_size].append(file)
            except OSError:
                continue

        return buckets

    async def _group_by_quick_hash(
        self,
        files: List[Path],
    ) -> Dict[str, List[Path]]:
        buckets: Dict[str, List[Path]] = defaultdict(list)
        total = len(files)

        for i, file in enumerate(files, start=1):
            if self._is_cancelled():
                return buckets

            try:
                # Key by size too, so different sizes never collide.
                digest = self._hash.calculate_partial(file)
                key = f"{file.stat().st_size}:{digest}"
                buckets[key].append(file)
            except OSError:
                pass

            if i % 200 == 0 or i == total:
                self._log(f"Quick hashing: {i}/{total}")
                await asyncio.sleep(0)

        return buckets

    async def _group_by_full_hash(
        self,
        files: List[Path],
    ) -> Dict[str, List[Path]]:
        buckets: Dict[str, List[Path]] = defaultdict(list)
        total = len(files)

        for i, file in enumerate(files, start=1):
            if self._is_cancelled():
                return buckets

            digest = self._hash.calculate(file, self._cancel_check)

            if digest is not None:
                buckets[digest].append(file)

            if i % 50 == 0 or i == total:
                self._log(f"Full hashing: {i}/{total}")
                await asyncio.sleep(0)

        return buckets

    def _build_groups(
        self,
        by_hash: Dict[str, List[Path]],
    ) -> List[DuplicateGroup]:
        groups: List[DuplicateGroup] = []

        for digest, members in by_hash.items():
            if len(members) < 2:
                continue

            ordered = sorted(members, key=self._file_time)

            keeper = ordered[0]
            duplicates = ordered[1:]

            groups.append(
                DuplicateGroup(
                    hash=digest,
                    size=keeper.stat().st_size,
                    keeper=keeper,
                    duplicates=duplicates,
                )
            )

        # Biggest reclaimable space first.
        groups.sort(key=lambda g: g.reclaimable_bytes, reverse=True)

        return groups

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _collision_candidates(
        self,
        buckets: Dict[object, List[Path]],
    ) -> List[Path]:
        candidates: List[Path] = []

        for members in buckets.values():
            if len(members) >= 2:
                candidates.extend(members)

        return candidates

    def _file_time(self, file: Path) -> float:
        stat = file.stat()

        birth = getattr(stat, "st_birthtime", None)

        # "Oldest" = earliest known timestamp for the file.
        return min(birth, stat.st_mtime) if birth else stat.st_mtime

    def _is_cancelled(self) -> bool:
        return self._cancel_check is not None and self._cancel_check()
