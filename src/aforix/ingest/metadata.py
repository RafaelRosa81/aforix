from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re


@dataclass(frozen=True)
class MeasurementMeta:
    station_id: str
    measurement_date: str
    measurement_time: str
    station_name: str | None = None


def clean_station_id(value: str | None, *, fallback: str | None = None) -> str:
    """Clean a station identifier without changing its identity.

    This helper only removes common file-name wrappers and unsafe separator
    characters. It deliberately does not map ``P<n>`` into any numeric
    namespace: station numbering belongs to the raw source and to the
    configurable metadata policy.
    """

    candidate = value if value else fallback

    if candidate:
        text = str(candidate).strip()

        # Common FlowTracker wrappers:
        # 70101.TXT.WAD -> 70101.TXT -> 70101
        # P71.TXT.WAD   -> P71.TXT   -> P71
        text = Path(text).stem

        if text.upper().endswith(".TXT"):
            text = Path(text).stem

        text = re.sub(r"[^A-Za-z0-9_-]+", "_", text).strip("_")

        if text:
            return text

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