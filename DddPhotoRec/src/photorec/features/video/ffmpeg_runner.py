import asyncio
import re
from pathlib import Path
from typing import Callable, Optional

#
# FFmpeg is a native binary (there is no pure-Python video encoder).
# `imageio-ffmpeg` ships a static build, so nothing needs to be installed on
# the system and it packages into the .exe.
#
try:
    import imageio_ffmpeg

    FFMPEG_EXE: Optional[str] = imageio_ffmpeg.get_ffmpeg_exe()
    FFMPEG_AVAILABLE = True
except Exception:
    FFMPEG_EXE = None
    FFMPEG_AVAILABLE = False


FileProgressCallback = Callable[[float], None]  # 0.0 .. 1.0
CancelCheck = Callable[[], bool]

_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")


async def probe_duration(source: Path) -> Optional[float]:
    """Total duration in seconds, parsed from ffmpeg's header read (fast)."""
    if not FFMPEG_AVAILABLE:
        return None

    process = await asyncio.create_subprocess_exec(
        FFMPEG_EXE,
        "-i",
        str(source),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )

    _stdout, stderr = await process.communicate()

    match = _DURATION_RE.search(stderr.decode(errors="ignore"))

    if not match:
        return None

    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


async def encode_h264(
    source: Path,
    destination: Path,
    crf: int,
    downscale_720: bool,
    progress: Optional[FileProgressCallback] = None,
    cancel_check: Optional[CancelCheck] = None,
) -> bool:
    """Re-encode `source` to H.264 `.mp4` at `destination`.

    Keeps resolution (unless `downscale_720`, which caps height at 720p without
    upscaling), preserves metadata/rotation, and copies the audio stream
    losslessly. Reports per-file progress (0..1) and can be cancelled (which
    kills ffmpeg). Returns True on success.
    """
    if not FFMPEG_AVAILABLE:
        return False

    duration = await probe_duration(source)

    args = [
        FFMPEG_EXE,
        "-y",
        "-i",
        str(source),
        "-c:v",
        "libx264",
        "-crf",
        str(crf),
        "-preset",
        "medium",
        "-c:a",
        "copy",
        "-map_metadata",
        "0",
        "-movflags",
        "+faststart",
    ]

    if downscale_720:
        # Cap height at 720; -2 keeps width even; never upscales.
        args += ["-vf", "scale=-2:min(720\\,ih)"]

    args += ["-progress", "pipe:1", "-nostats", "-loglevel", "error", str(destination)]

    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        while True:
            if cancel_check is not None and cancel_check():
                process.kill()
                await process.wait()
                return False

            line = await process.stdout.readline()

            if not line:
                break

            text = line.decode(errors="ignore").strip()

            if text.startswith("out_time_us=") and duration and progress:
                try:
                    microseconds = int(text.split("=", 1)[1])
                    progress(min(microseconds / 1_000_000 / duration, 1.0))
                except (ValueError, ZeroDivisionError):
                    pass
            elif text == "progress=end" and progress:
                progress(1.0)

        await process.wait()
        return process.returncode == 0
    except Exception:
        try:
            process.kill()
            await process.wait()
        except Exception:
            pass
        return False
