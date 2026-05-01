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
    """Normalize station ID values extracted from source files."""

    if value:
        text = str(value).strip()

        # Common FlowTracker case:
        # CHAM1512.WAD -> CHAM1512
        # P82001.TXT.WAD -> P82001.TXT -> P82001
        text = Path(text).stem

        if text.upper().endswith(".TXT"):
            text = Path(text).stem

        text = re.sub(r"[^A-Za-z0-9_-]+", "_", text).strip("_")

        if text:
            return text.upper()

    if fallback:
        return str(fallback).strip().upper()

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