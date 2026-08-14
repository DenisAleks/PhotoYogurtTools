import re
from datetime import datetime
from pathlib import Path
from typing import Optional

#
# Friendly tokens -> strftime codes. Order matters: longer tokens must be
# translated first (YYYY before YY, MMMM before MMM before MM), so we sort
# by descending length before substituting.
#
_TOKENS = {
    "YYYY": "%Y",   # 2024
    "YY": "%y",     # 24
    "MMMM": "%B",   # October
    "MMM": "%b",    # Oct
    "MM": "%m",     # 10
    "DD": "%d",     # 05
    "HH": "%H",     # 14 (24h)
    "hh": "%I",     # 02 (12h)
    "mm": "%M",     # 30
    "ss": "%S",     # 22
}

# Characters not allowed in file/folder names on common filesystems.
_ILLEGAL = re.compile(r'[<>:"\\|?*\x00-\x1f]')

# A "/" in the pattern means "make a subfolder here".
_PATH_SEPARATOR = "/"

_MAX_COMPONENT_LENGTH = 120


class NameBuilder:
    """Builds a relative destination path from a user pattern.

    Example pattern: ``YYYY/MM/YYYY-MM-DD_HH-mm-ss_{loc}``
    Non-date tokens: ``{name}`` (original stem), ``{loc}`` (place name).
    """

    def build(
        self,
        pattern: str,
        date: datetime,
        original_stem: str,
        extension: str,
        place: Optional[str] = None,
    ) -> Path:
        text = self._apply_date_tokens(pattern, date)

        text = text.replace("{name}", original_stem)
        text = text.replace("{loc}", place or "")

        parts = [
            self._clean(part)
            for part in text.split(_PATH_SEPARATOR)
        ]

        parts = [part for part in parts if part]

        if not parts:
            parts = [self._clean(original_stem) or "file"]

        relative = Path(*parts)

        return relative.with_name(
            relative.name + self._normalize_extension(extension)
        )

    # ------------------------------------------------------------------
    # INTERNAL
    # ------------------------------------------------------------------

    def _apply_date_tokens(self, pattern: str, date: datetime) -> str:
        strftime_pattern = pattern

        for token in sorted(_TOKENS, key=len, reverse=True):
            strftime_pattern = strftime_pattern.replace(
                token,
                _TOKENS[token],
            )

        return date.strftime(strftime_pattern)

    def _clean(self, part: str) -> str:
        part = _ILLEGAL.sub("", part)
        part = re.sub(r"\s+", " ", part).strip()

        # Collapse separators left dangling by an empty {loc} / {name}.
        part = re.sub(r"_{2,}", "_", part)
        part = re.sub(r"-{2,}", "-", part)
        part = part.strip("_-. ")

        return part[:_MAX_COMPONENT_LENGTH]

    def _normalize_extension(self, extension: str) -> str:
        extension = extension.lower()

        if extension and not extension.startswith("."):
            extension = "." + extension

        return extension
