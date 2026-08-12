from hashlib import sha256
from pathlib import Path
from typing import Callable


class HashCalculator:

    CHUNK_SIZE = 8 * 1024 * 1024

    def calculate(
        self,
        file: Path,
        cancel_check: Callable[[], bool] | None = None,
    ) -> str | None:

        hasher = sha256()

        with file.open("rb") as f:

            while chunk := f.read(self.CHUNK_SIZE):

                if cancel_check is not None and cancel_check():
                    return None

                hasher.update(chunk)

        return hasher.hexdigest()