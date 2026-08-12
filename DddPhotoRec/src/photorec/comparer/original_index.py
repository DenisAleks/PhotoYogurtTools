from collections import defaultdict
from pathlib import Path

from photorec.models.file_info import FileInfo
from photorec.utils.hash_calculator import HashCalculator


class OriginalIndex:

    def __init__(self) -> None:
        self._sizes = defaultdict(list)
        self._hash = HashCalculator()

    @property
    def count(self) -> int:
        return sum(len(v) for v in self._sizes.values())

    def build(
            self,
            files: list[Path],
            progress=None,
    ):
        self._sizes.clear()

        for i, file in enumerate(files, start=1):

            info = FileInfo(
                path=file,
                size=file.stat().st_size,
            )

            self._sizes[info.size].append(info)

            if progress and i % 500 == 0:
                progress(i, len(files))


        #
        # Hash only groups having same size
        #

        for infos in self._sizes.values():

            if len(infos) < 2:
                continue

            for info in infos:
                info.hash = self._hash.calculate(info.path)

    def get_candidates(self, size: int) -> list[FileInfo]:
        return self._sizes.get(size, [])