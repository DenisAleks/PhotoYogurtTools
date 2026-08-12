import json
from pathlib import Path


class HashCache:

    def __init__(self, cache_file: Path) -> None:
        self._cache_file = cache_file
        self._data: dict[str, dict] = {}

        self._load()

    def _load(self) -> None:
        if not self._cache_file.exists():
            return

        try:
            self._data = json.loads(
                self._cache_file.read_text(encoding="utf-8")
            )
        except (json.JSONDecodeError, OSError):
            self._data = {}

    def get(self, file: Path) -> str | None:
        key = str(file.absolute())

        entry = self._data.get(key)

        if entry is None:
            return None

        try:
            stat = file.stat()
        except OSError:
            return None

        if entry["size"] != stat.st_size:
            return None

        if entry["mtime_ns"] != stat.st_mtime_ns:
            return None

        return entry["hash"]

    def put(
        self,
        file: Path,
        hash_value: str,
    ) -> None:

        stat = file.stat()

        self._data[str(file.absolute())] = {
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "hash": hash_value,
        }

    def save(self) -> None:
        self._cache_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._cache_file.write_text(
            json.dumps(
                self._data,
                indent=2,
            ),
            encoding="utf-8",
        )

    @property
    def count(self) -> int:
        return len(self._data)