from pathlib import Path


class RecoveredIndex:

    def __init__(self) -> None:
        self._hashes: dict[str, Path] = {}

    def contains(self, hash_value: str) -> bool:
        return hash_value in self._hashes

    def add(
        self,
        hash_value: str,
        file: Path,
    ) -> None:
        self._hashes[hash_value] = file

    @property
    def count(self) -> int:
        return len(self._hashes)

