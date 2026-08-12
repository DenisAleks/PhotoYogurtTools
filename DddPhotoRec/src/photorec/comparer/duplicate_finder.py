from pathlib import Path

from photorec.comparer.original_index import OriginalIndex
from photorec.models.file_info import FindResult
from photorec.utils.hash_calculator import HashCalculator


class DuplicateFinder:
    def __init__(
            self,
            index: OriginalIndex,
            cancel_check=None,
    ):
        self._index = index
        self._hash = HashCalculator()
        self._cancel_check = cancel_check

    def find_original(
            self,
            recovered: Path,
    ) -> FindResult | None:

        candidates = self._index.get_candidates(
            recovered.stat().st_size
        )

        if not candidates:
            return None

        recovered_hash = self._hash.calculate(
            recovered,
            self._cancel_check,
        )

        if recovered_hash is None:
            return None

        for candidate in candidates:

            if self._cancel_check is not None and self._cancel_check():
                return None

            if candidate.hash is None:
                candidate.hash = self._hash.calculate(
                    candidate.path,
                    self._cancel_check,
                )

                if candidate.hash is None:
                    return None

            if candidate.hash == recovered_hash:
                return candidate.path

        return None