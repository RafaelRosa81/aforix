from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re

from aforix.metadata import canonical_station_id


@dataclass(frozen=True)
class MeasurementMeta:
    station_id: str
    measurement_date: str
    measurement_time: str
    station_name: str | None = None


def clean_station_id(value: str | None, *, fallback: str | None = None) -> str:
    """Normalize station IDs extracted from source files.

    File-like wrappers are removed first, then the shared Aforix canonical
    station-id rule is applied. This keeps ingest compatible with FlowTracker
    names such as ``P71.TXT.WAD`` while ensuring legacy ``P<n>`` identifiers
    enter the canonical 7000 namespace exactly once.
    """

    candidate = value if value else fallback

    if candidate:
        text = str(candidate).strip()

        # Common FlowTracker case:
        # CHAM1512.WAD -> CHAM1512
        # P71.TXT.WAD -> P71.TXT -> P71 -> 7071
        text = Path(text).stem

        if text.upper().endswith(".TXT"):
            text = Path(text).stem

        text = re.sub(r"[^A-Za-z0-9_-]+", "_", text).strip("_")

        if text:
            return canonical_station_id(text)

    return "UNKNOWN"


def clean_station_name(value: str | None) -> str | None:
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    return text


def datetime_to_parts(dt: datetime) -> tuple[str, str]:
    return dt.strftime("%Y%m%d"), dt.strftime("%H%M%S")