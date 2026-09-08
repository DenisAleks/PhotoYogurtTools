import shutil
from pathlib import Path
from typing import Callable, List, Optional, Set

from photorec.features.video.ffmpeg_runner import (
    FFMPEG_AVAILABLE,
    encode_h264,
)
from photorec.shared.image_signature import is_image
from photorec.shared.media_scanner import MediaScanner


LogCallback = Callable[[str], None]
CancelCheck = Callable[[], bool]
ProgressCallback = Callable[[int, int], None]     # overall: done files / total
FileProgressCallback = Callable[[float], None]    # current file: 0.0 .. 1.0

BACKUP_FOLDER_NAME = "_Backup"

# Quality preset label -> libx264 CRF (lower = higher quality / bigger).
CRF_BY_QUALITY = {
    "High": 20,
    "Medium": 23,
    "Strong": 26,
}


class VideoCompressorService:
    """Re-encodes videos to H.264 (.mp4) in place, keeping originals in _Backup/.

    Resolution is kept, unless a video's original file size exceeds the chosen
    threshold and downscaling is enabled, in which case it is capped at 720p.
    A compressed file replaces the original only if it is actually smaller.
    """

    def __init__(
        self,
        input_folder: str,
        crf: int = 23,
        downscale_720: bool = False,
        threshold_mb: float = 500.0,
        log: Optional[LogCallback] = None,
        cancel_check: Optional[CancelCheck] = None,
        progress: Optional[ProgressCallback] = None,
        file_progress: Optional[FileProgressCallback] = None,
    ) -> None:
        self._input = Path(input_folder)
        self._crf = crf
        self._downscale = downscale_720
        self._threshold = int(threshold_mb * 1024 * 1024)
        self._backup_root = self._input / BACKUP_FOLDER_NAME

        self._log_callback = log
        self._cancel_check = cancel_check
        self._progress = progress
        self._file_progress = file_progress

    async def run(self) -> None:
        if not FFMPEG_AVAILABLE:
            self._log("ERROR: ffmpeg is not available (install imageio-ffmpeg).")
            return

        self._log(f"Scanning: {self._input}")

        files = MediaScanner(str(self._input)).scan()
        videos = [
            f
            for f in files
            if not is_image(f) and self._backup_root not in f.parents
        ]

        self._log(f"Videos found: {len(videos)}")
        self._log(
            f"Quality: CRF {self._crf} · "
            f"Downscale >{self._human(self._threshold)} to 720p: "
            f"{'yes' if self._downscale else 'no'}"
        )

        if not videos:
            self._log("No videos to compress.")
            return

        planned: Set[Path] = set()

        compressed = skipped = failed = 0
        total_before = total_after = 0
        total = len(videos)

        for i, video in enumerate(videos, start=1):
            if self._is_cancelled():
                self._log(f"Cancelled at {i - 1}/{total}.")
                return

            before = video.stat().st_size
            downscale_this = self._downscale and before > self._threshold

            self._log(
                f"[{i}/{total}] {video.name} "
                f"({self._human(before)}"
                f"{', → 720p' if downscale_this else ''})"
            )

            self._set_file_progress(0.0)

            temp = video.with_name(f"{video.stem}.__enc__.mp4")

            ok = await encode_h264(
                source=video,
                destination=temp,
                crf=self._crf,
                downscale_720=downscale_this,
                progress=self._set_file_progress,
                cancel_check=self._is_cancelled,
            )

            if self._is_cancelled():
                self._cleanup(temp)
                self._log(f"Cancelled at {i - 1}/{total}.")
                return

            if not ok or not temp.exists():
                failed += 1
                self._cleanup(temp)
                self._log("   failed — kept original.")
                self._report_overall(i, total)
                continue

            after = temp.stat().st_size

            # Keep the result only if it actually saved space.
            if after >= before:
                skipped += 1
                self._cleanup(temp)
                self._log(f"   no size benefit ({self._human(after)}) — kept original.")
            else:
                self._backup(video)

                destination = self._reserve(video.with_suffix(".mp4"), planned)
                shutil.move(str(temp), str(destination))

                compressed += 1
                total_before += before
                total_after += after
                self._log(
                    f"   {self._human(before)} → {self._human(after)}"
                )

            self._report_overall(i, total)

        saved = total_before - total_after
        percent = (saved / total_before * 100) if total_before else 0.0

        self._log("")
        self._log("Video compression finished")
        self._log(f"Compressed : {compressed}")
        self._log(f"Skipped    : {skipped}  (no size benefit)")
        if failed:
            self._log(f"Failed     : {failed}")
        self._log(f"Saved      : {self._human(saved)} ({percent:.1f}%)")
        if compressed:
            self._log(
                f"Originals backed up in: {BACKUP_FOLDER_NAME}/ "
                "(delete it once you're happy)."
            )

    # ------------------------------------------------------------------
    # INTERNAL
    # ------------------------------------------------------------------

    def _backup(self, video: Path) -> None:
        relative = video.relative_to(self._input)
        destination = self._backup_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(video), str(destination))

    def _reserve(self, relative_path: Path, planned: Set[Path]) -> Path:
        destination = relative_path

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

    def _cleanup(self, temp: Path) -> None:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass

    def _human(self, size: int) -> str:
        value = float(size)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024 or unit == "TB":
                if unit == "B":
                    return f"{int(value)} {unit}"
                return f"{value:.1f} {unit}"
            value /= 1024
        return f"{size} B"

    def _set_file_progress(self, fraction: float) -> None:
        if self._file_progress is not None:
            self._file_progress(fraction)

    def _report_overall(self, done: int, total: int) -> None:
        self._set_file_progress(0.0)
        if self._progress is not None:
            self._progress(done, total)

    def _is_cancelled(self) -> bool:
        return self._cancel_check is not None and self._cancel_check()

    def _log(self, message: str) -> None:
        if self._log_callback is not None:
            self._log_callback(message)
