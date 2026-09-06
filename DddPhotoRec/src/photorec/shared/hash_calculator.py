from hashlib import sha256
from pathlib import Path
from typing import Callable, Optional


class HashCalculator:
    """SHA-256 hashing for media files.

    `calculate` reads the whole file (cancellable mid-file). `calculate_partial`
    reads only a prefix - a cheap first-pass filter before committing to a full
    read when comparing many same-size files.
    """

    CHUNK_SIZE = 8 * 1024 * 1024

    PARTIAL_SIZE = 64 * 1024

    def calculate(
        self,
        file: Path,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> Optional[str]:

        hasher = sha256()

        with file.open("rb") as f:

            while chunk := f.read(self.CHUNK_SIZE):

                if cancel_check is not None and cancel_check():
                    return None

                hasher.update(chunk)

        return hasher.hexdigest()

    def calculate_partial(
        self,
        file: Path,
        max_bytes: Optional[int] = None,
    ) -> Optional[str]:

        limit = max_bytes or self.PARTIAL_SIZE

        hasher = sha256()

        with file.open("rb") as f:
            hasher.update(f.read(limit))

        return hasher.hexdigest()
