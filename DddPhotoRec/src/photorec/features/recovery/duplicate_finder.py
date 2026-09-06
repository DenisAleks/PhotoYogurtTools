from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from photorec.features.recovery.image_signature import (
    image_signature,
    is_image,
)
from photorec.features.recovery.original_index import OriginalIndex
from photorec.shared.hash_calculator import HashCalculator


@dataclass(slots=True)
class MatchResult:
    # The matched library file, or None if the recovered file is not a duplicate.
    original: Optional[Path]
    # For images: a library photo shares this file's dimensions (diagnostics).
    had_dimension_match: bool


class DuplicateFinder:
    """Decides whether a recovered file already exists in the library.

    Images are matched by decoded-pixel content (robust to recovery padding
    and EXIF differences); videos by exact bytes.
    """

    def __init__(
        self,
        index: OriginalIndex,
        cancel_check=None,
    ) -> None:
        self._index = index
        self._cancel_check = cancel_check
        self._byte_hash = HashCalculator()

    def find_original(self, recovered: Path) -> MatchResult:
        if is_image(recovered):
            dimensions, signature = image_signature(recovered)

            if signature is None:
                return MatchResult(None, False)

            had_dimension_match = (
                dimensions is not None
                and self._index.has_image_dimensions(dimensions)
            )

            return MatchResult(
                original=self._index.get_original(signature),
                had_dimension_match=had_dimension_match,
            )

        signature = self._byte_hash.calculate(
            recovered,
            self._cancel_check,
        )

        if signature is None:
            return MatchResult(None, False)

        return MatchResult(
            original=self._index.get_original(signature),
            had_dimension_match=False,
        )
