import asyncio
import shutil
from pathlib import Path
from typing import Callable, Optional, Set, Tuple

from photorec.features.compressor.encoder import (
    QUALITY_FLOOR,
    encode_jpeg_to_target,
)
from photorec.shared.image_signature import is_image
from photorec.shared.media_scanner import MediaScanner


LogCallback = Callable[[str], None]
CancelCheck = Callable[[], bool]
ProgressCallback = Callable[[int, int], None]

# Formats converted to JPEG when the "convert to JPEG" option is on.
CONVERT_TO_JPEG_EXT = {".heic", ".heif", ".png"}
JPEG_EXT = {".jpg", ".jpeg"}

# Folders created inside the input folder in "in place" mode.
BACKUP_FOLDER_NAME = "_Backup"
VIDEO_FOLDER_NAME = "_Video"


class CompressorService:
    """Compresses photos, either into an OUTPUT folder or in place.

    - **OUTPUT mode** (default): compressed copies go to OUTPUT; originals and
      videos are left untouched.
    - **In-place mode**: originals are moved to `_Backup/` (mirroring structure)
      and replaced by the compressed version in the same folder; videos are
      moved to `_Video/`. Both `_Backup/` and `_Video/` are skipped on re-runs.

    In both modes: resolution is never changed, EXIF/ICC are preserved, and
    HEIC/HEIF/PNG can be converted to JPEG.
    """

    def __init__(
        self,
        input_folder: str,
        output_folder: Optional[str] = None,
        convert_to_jpeg: bool = True,
        in_place: bool = False,
        target_mb: float = 2.0,
        log: Optional[LogCallback] = None,
        cancel_check: Optional[CancelCheck] = None,
        progress: Optional[ProgressCallback] = None,
    ) -> None:
        self._input = Path(input_folder)
        self._output = Path(output_folder) if output_folder else None
        self._convert = convert_to_jpeg
        self._in_place = in_place
        self._target = int(target_mb * 1024 * 1024)

        self._log_callback = log
        self._cancel_check = cancel_check
        self._progress = progress

        if in_place:
            self._dest_root = self._input
            self._backup_root: Optional[Path] = self._input / BACKUP_FOLDER_NAME
            self._video_root: Optional[Path] = self._input / VIDEO_FOLDER_NAME
        else:
            self._dest_root = self._output
            self._backup_root = None
            self._video_root = None

    async def run(self) -> None:
        mode = "IN PLACE (originals → _Backup)" if self._in_place else "into OUTPUT"

        self._log(f"Scanning: {self._input}")
        self._log(
            f"Mode: {mode} · Target <= {self._human(self._target)} · "
            f"Convert HEIC/HEIF/PNG to JPEG: {'yes' if self._convert else 'no'}"
        )

        files = MediaScanner(str(self._input)).scan()
        files = [f for f in files if not self._is_own_folder(f)]

        images = [f for f in files if is_image(f)]
        videos = [f for f in files if not is_image(f)]

        self._log(f"Images: {len(images)} · Videos: {len(videos)}")

        moved_videos = 0
        if videos:
            if self._in_place:
                moved_videos = self._relocate_videos(videos)
            else:
                self._log(f"Videos skipped: {len(videos)}")

        if not images:
            self._log("No images to compress.")
            return

        planned: Set[Path] = set()

        converted = recompressed = copied = failed = over_target = 0
        total_before = total_after = 0
        total = len(images)

        for i, file in enumerate(images, start=1):
            if self._is_cancelled():
                self._log(f"Cancelled at {i - 1}/{total}.")
                return

            action, before, after, fits = self._process_one(file, planned)

            total_before += before
            total_after += after

            if action == "convert":
                converted += 1
            elif action == "recompress":
                recompressed += 1
            elif action == "copy":
                copied += 1
            elif action == "fail":
                failed += 1

            if action in ("convert", "recompress") and not fits:
                over_target += 1

            self._report(i, total)

            if i % 25 == 0 or i == total:
                self._log(
                    f"Progress: {i}/{total} ({i / total * 100:.1f}%) | "
                    f"converted={converted}, recompressed={recompressed}, "
                    f"copied={copied}"
                )
                await asyncio.sleep(0)

        saved = total_before - total_after
        percent = (saved / total_before * 100) if total_before else 0.0

        self._log("")
        self._log("Compression finished")
        self._log(f"Converted to JPEG : {converted}")
        self._log(f"Recompressed JPEG : {recompressed}")
        if self._in_place:
            self._log(f"Left unchanged     : {copied}")
        else:
            self._log(f"Copied unchanged  : {copied}")
        if failed:
            self._log(f"Failed (kept)     : {failed}")
        if self._in_place:
            self._log(f"Videos moved      : {moved_videos}  (to {VIDEO_FOLDER_NAME}/)")
        else:
            self._log(f"Videos skipped    : {len(videos)}")
        self._log(f"Original size     : {self._human(total_before)}")
        self._log(f"New size          : {self._human(total_after)}")
        self._log(f"Saved             : {self._human(saved)} ({percent:.1f}%)")

        if self._in_place:
            self._log(
                f"Originals backed up in: {BACKUP_FOLDER_NAME}/ "
                "(delete it once you're happy)."
            )

        if over_target:
            self._log("")
            self._log(
                f"NOTE: {over_target} file(s) couldn't reach "
                f"{self._human(self._target)} without dropping below quality "
                f"{QUALITY_FLOOR}; kept at best effort (resolution unchanged)."
            )

    # ------------------------------------------------------------------
    # INTERNAL
    # ------------------------------------------------------------------

    def _process_one(
        self,
        file: Path,
        planned: Set[Path],
    ) -> Tuple[str, int, int, bool]:
        extension = file.suffix.lower()
        before = file.stat().st_size
        relative = file.relative_to(self._input)

        is_jpeg = extension in JPEG_EXT
        convert = self._convert and extension in CONVERT_TO_JPEG_EXT
        oversized = before > self._target

        if convert or (is_jpeg and oversized):
            # Never enlarge a file, and never exceed the global target.
            effective_target = min(self._target, before)
            result = encode_jpeg_to_target(file, effective_target)

            if result is None:
                # Corrupt / unreadable — keep the original safely.
                self._keep_original(file, relative, planned)
                return "fail", before, before, True

            data, _quality, _fits = result

            # Recompressing an already-small JPEG that didn't shrink: keep it.
            if not convert and len(data) >= before:
                self._keep_original(file, relative, planned)
                return "copy", before, before, True

            if self._in_place:
                # Free the original slot (and preserve it) before writing.
                self._backup(file, relative)

            destination = self._reserve(relative.with_suffix(".jpg"), planned)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)

            action = "convert" if convert else "recompress"
            return action, before, len(data), len(data) <= self._target

        # Small enough and not being converted.
        self._keep_original(file, relative, planned)
        return "copy", before, before, True

    def _keep_original(
        self,
        file: Path,
        relative: Path,
        planned: Set[Path],
    ) -> None:
        # In place: leave it where it is. Into OUTPUT: copy it across.
        if not self._in_place:
            self._copy(file, self._reserve(relative, planned))

    def _relocate_videos(self, videos) -> int:
        moved = 0
        planned: Set[Path] = set()

        for video in videos:
            if self._is_cancelled():
                break

            relative = video.relative_to(self._input)
            destination = self._reserve_under(
                self._video_root, relative, planned
            )
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(video), str(destination))
            moved += 1

        self._log(f"Videos moved to {VIDEO_FOLDER_NAME}/: {moved}")
        return moved

    def _backup(self, file: Path, relative: Path) -> None:
        destination = self._backup_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(file), str(destination))

    def _is_own_folder(self, file: Path) -> bool:
        # Ignore our own _Backup / _Video trees on re-runs.
        if not self._in_place:
            return False
        return (
            self._backup_root in file.parents
            or self._video_root in file.parents
        )

    def _reserve(self, relative: Path, planned: Set[Path]) -> Path:
        return self._reserve_under(self._dest_root, relative, planned)

    def _reserve_under(
        self,
        root: Path,
        relative: Path,
        planned: Set[Path],
    ) -> Path:
        destination = root / relative

        if destination not in planned and not destination.exists():
            planned.add(destination)
            return destination

        stem = destination.stem
        suffix = destination.suffix
        parent = destination.parent
        counter = 1

        while True:
            candidate = parent / f"{stem}_{counter}{suffix}"
            if candidate not in planned and not candidate.exists():
                planned.add(candidate)
                return candidate
            counter += 1

    def _copy(self, source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    def _human(self, size: int) -> str:
        value = float(size)

        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024 or unit == "TB":
                if unit == "B":
                    return f"{int(value)} {unit}"
                return f"{value:.1f} {unit}"
            value /= 1024

        return f"{size} B"

    def _report(self, done: int, total: int) -> None:
        if self._progress is not None:
            self._progress(done, total)

    def _is_cancelled(self) -> bool:
        return self._cancel_check is not None and self._cancel_check()

    def _log(self, message: str) -> None:
        if self._log_callback is not None:
            self._log_callback(message)
