from pathlib import Path

from photorec.features.recovery.original_index import OriginalIndex
from photorec.features.recovery.models import FindResult
from photorec.features.recovery.hash_calculator import HashCalculator


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
    ) -> Path | None:

        recovered_size = recovered.stat().st_size

        # print()
        # print("=" * 80)
        # print(f"RECOVERED: {recovered}")
        # print(f"SIZE:      {recovered_size}")

        candidates = self._index.get_candidates(
            recovered_size
        )

        # print(f"CANDIDATES: {len(candidates)}")

        if not candidates:
            # print("RESULT: UNIQUE - no same-size original")
            return None

        recovered_hash = self._hash.calculate(
            recovered,
            self._cancel_check,
        )

        # print(f"REC HASH: {recovered_hash}")

        if recovered_hash is None:
            # print("RESULT: CANCELLED")
            return None

        for candidate in candidates:

            # print(
            #     f"CANDIDATE: {candidate.path}"
            # )
            #
            # print(
            #     f"  size: {candidate.size}"
            # )

            if candidate.hash is None:
                candidate.hash = self._hash.calculate(
                    candidate.path,
                    self._cancel_check,
                )

            # print(
            #     f"  hash: {candidate.hash}"
            # )

            if candidate.hash == recovered_hash:
                # print("RESULT: DUPLICATE")
                return candidate.path

        # print("RESULT: UNIQUE - hash mismatch")

        return None