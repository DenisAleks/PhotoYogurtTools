from pathlib import Path
from typing import Dict, Optional, Tuple

from photorec.features.renamer.exif_reader import ExifReader

#
# Offline reverse geocoding. `reverse_geocode` bundles a city dataset and
# resolves coordinates to the nearest city entirely on-device - no network,
# so GPS coordinates never leave the machine. If the package is missing,
# location is silently disabled and {loc} resolves to empty.
#
try:
    import reverse_geocode

    GEOCODING_AVAILABLE = True
except Exception:
    reverse_geocode = None
    GEOCODING_AVAILABLE = False


class Geocoder:
    """Turns a file's EXIF GPS into a human place name (offline)."""

    def __init__(self) -> None:
        self._exif = ExifReader()
        self._cache: Dict[Tuple[float, float], Optional[str]] = {}

    @property
    def available(self) -> bool:
        return GEOCODING_AVAILABLE

    def place_for(self, file: Path) -> Optional[str]:
        if not GEOCODING_AVAILABLE:
            return None

        coordinates = self._exif.read_gps(file)

        if coordinates is None:
            return None

        # Round so nearby shots share a cache entry (and a place name).
        key = (round(coordinates[0], 3), round(coordinates[1], 3))

        if key in self._cache:
            return self._cache[key]

        place = self._lookup(coordinates)
        self._cache[key] = place

        return place

    def _lookup(self, coordinates: Tuple[float, float]) -> Optional[str]:
        try:
            result = reverse_geocode.search([coordinates])[0]
        except Exception:
            return None

        return result.get("city") or result.get("country")
