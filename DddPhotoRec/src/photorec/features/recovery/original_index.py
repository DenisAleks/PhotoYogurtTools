import asyncio
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

from photorec.features.recovery.image_signature import (
    Dimensions,
    image_signature,
    is_image,
)
from photorec.shared.hash_calculator import HashCalculator


LogCallback = Callable[[str], None]
CancelCheck = Callable[[], bool]


class OriginalIndex:
    """Content index of the library.

    Maps a content signature -> a library file:
      - images: SHA-256 of the decoded pixels (survives padding / EXIF changes)
      - videos: SHA-256 of the raw bytes

    Also remembers the set of image dimensions seen, used only for diagnostics
    (telling "genuinely new" apart from "same dimensions, different pixels").
    """

    def __init__(self) -> None:
        self._by_signature: Dict[str, Path] = {}
        self._image_dimensions: Set[Dimensions] = set()
        self._byte_hash = HashCalculator()

    @property
    def count(self) -> int:
        return len(self._by_signature)

    async def build(
        self,
        files: List[Path],
        log: Optional[LogCallback] = None,
        cancel_check: Optional[CancelCheck] = None,
    ) -> None:
        self._by_signature.clear()
        self._image_dimensions.clear()

        total = len(files)

        for i, file in enumerate(files, start=1):
            if cancel_check is not None and cancel_check():
                return

            self._add(file)

            if i % 50 == 0 or i == total:
                if log is not None:
                    log(f"Indexing library: {i}/{total}")

                await asyncio.sleep(0)

    def get_original(self, signature: str) -> Optional[Path]:
        return self._by_signature.get(signature)

    def has_image_dimensions(self, dimensions: Dimensions) -> bool:
        return dimensions in self._image_dimensions

    # ------------------------------------------------------------------
    # INTERNAL
    # ------------------------------------------------------------------

    def _add(self, file: Path) -> None:
        if is_image(file):
            dimensions, signature = image_signature(file)

            if dimensions is not None:
                self._image_dimensions.add(dimensions)
        else:
            signature = self._byte_hash.calculate(file)

        if signature is not None:
            # First file wins; later library copies map to the same signature.
            self._by_signature.setdefault(signature, file)
