import asyncio
from collections import defaultdict
from pathlib import Path
from typing import Callable, Dict, List, Optional

from photorec.features.duplicates.models import DuplicateGroup
from photorec.shared.hash_calculator import HashCalculator
from photorec.shared.image_signature import (
    image_signature,
    is_image,
    read_dimensions,
)


CancelCheck = Callable[[], bool]
LogCallback = Callable[[], None]
ProgressCallback = Callable[[int, int], None]


class DuplicateScanner:
    """Finds duplicate media files within one folder.

    - Images are matched by **decoded pixel content**, so copies that differ
      only in padding or EXIF still group together. A cheap dimensions pass
      filters candidates before the expensive decode.
    - Videos are matched by **exact bytes** via a size -> quick-hash ->
      full-hash funnel (pixels can't be cheaply decoded).
    """

    def __init__(
        self,
        cancel_check: Optional[CancelCheck] = None,
        log: Optional[Callable[[str], None]] = None,
        progress: Optional[ProgressCallback] = None,
    ) -> None:
        self._cancel_check = cancel_check
        self._log = log or (lambda _msg: None)
        self._progress = progress
        self._hash = HashCalculator()

    def _report(self, done: int, total: int) -> None:
        if self._progress is not None:
            self._progress(done, total)

    async def scan(self, files: List[Path]) -> List[DuplicateGroup]:
        images = [f for f in files if is_image(f)]
        videos = [f for f in files if not is_image(f)]

        self._log(f"Images: {len(images)} · Videos: {len(videos)}")

        groups: List[DuplicateGroup] = []
        groups += await self._scan_images(images)
        groups += await self._scan_videos(videos)

        # Biggest reclaimable space first.
        groups.sort(key=lambda g: g.reclaimable_bytes, reverse=True)

        return groups

    # ------------------------------------------------------------------
    # IMAGES (pixel content)
    # ------------------------------------------------------------------

    async def _scan_images(
        self,
        images: List[Path],
    ) -> List[DuplicateGroup]:
        if not images:
            return []

        # Stage 1: cheap dimensions pass (no decode).
        by_dimensions: Dict[object, List[Path]] = defaultdict(list)
        total = len(images)

        for i, file in enumerate(images, start=1):
            if self._is_cancelled():
                return []

            dimensions = read_dimensions(file)

            if dimensions is not None:
                by_dimensions[dimensions].append(file)

            if i % 200 == 0 or i == total:
                self._log(f"Reading image sizes: {i}/{total}")
                self._report(i, total)
                await asyncio.sleep(0)

        candidates = self._collision_candidates(by_dimensions)
        self._log(f"Same-dimension image candidates: {len(candidates)}")

        if not candidates:
            return []

        # Stage 2: decode + pixel-hash only the candidates.
        by_pixels: Dict[str, List[Path]] = defaultdict(list)
        total = len(candidates)

        for i, file in enumerate(candidates, start=1):
            if self._is_cancelled():
                return []

            _dimensions, signature = image_signature(file)

            if signature is not None:
                by_pixels[signature].append(file)

            if i % 50 == 0 or i == total:
                self._log(f"Hashing image pixels: {i}/{total}")
                self._report(i, total)
                await asyncio.sleep(0)

        return self._build_groups(by_pixels)

    # ------------------------------------------------------------------
    # VIDEOS (exact bytes)
    # ------------------------------------------------------------------

    async def _scan_videos(
        self,
        videos: List[Path],
    ) -> List[DuplicateGroup]:
        if not videos:
            return []

        by_size: Dict[int, List[Path]] = defaultdict(list)

        for file in videos:
            try:
                by_size[file.stat().st_size].append(file)
            except OSError:
                continue

        size_candidates = self._collision_candidates(by_size)

        if not size_candidates:
            return []

        by_quick = await self._group_by_quick_hash(size_candidates)
        quick_candidates = self._collision_candidates(by_quick)

        if not quick_candidates:
            return []

        by_full = await self._group_by_full_hash(quick_candidates)

        return self._build_groups(by_full)

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
                digest = self._hash.calculate_partial(file)
                key = f"{file.stat().st_size}:{digest}"
                buckets[key].append(file)
            except OSError:
                pass

            if i % 200 == 0 or i == total:
                self._log(f"Quick hashing videos: {i}/{total}")
                self._report(i, total)
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

            if i % 20 == 0 or i == total:
                self._log(f"Full hashing videos: {i}/{total}")
                self._report(i, total)
                await asyncio.sleep(0)

        return buckets

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _build_groups(
        self,
        by_signature: Dict[str, List[Path]],
    ) -> List[DuplicateGroup]:
        groups: List[DuplicateGroup] = []

        for signature, members in by_signature.items():
            if len(members) < 2:
                continue

            ordered = sorted(members, key=self._file_time)

            keeper = ordered[0]

            try:
                size = keeper.stat().st_size
            except OSError:
                size = 0

            groups.append(
                DuplicateGroup(
                    hash=signature,
                    size=size,
                    keeper=keeper,
                    duplicates=ordered[1:],
                )
            )

        return groups

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
