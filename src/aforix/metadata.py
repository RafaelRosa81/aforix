from __future__ import annotations

import re
from datetime import date, datetime, time
from typing import Any

import pandas as pd


DEFAULT_DATE_INPUT_FORMATS = [
    "%Y%m%d",
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%m/%d/%Y",
    "%d/%m/%Y",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%m/%d/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
]

DEFAULT_TIME_INPUT_FORMATS = [
    "%H%M%S",
    "%H:%M:%S",
    "%H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%m/%d/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
]


_EMPTY_STRINGS = {"", "nan", "none", "null", "nat", "<na>"}


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except Exception:
        pass
    return str(value).strip().lower() in _EMPTY_STRINGS


def _as_clean_string(value: Any) -> str:
    if _is_empty(value):
        return ""

    if isinstance(value, float) and value.is_integer():
        return str(int(value))

    text = str(value).strip()
    if text.endswith(".0"):
        return text[:-2]
    return text


def _parse_datetime_with_formats(value: Any, input_formats: list[str]) -> datetime | None:
    if _is_empty(value):
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, date) and not isinstance(value, datetime):
        return datetime.combine(value, time.min)

    if isinstance(value, time):
        return datetime.combine(date.today(), value)

    text = _as_clean_string(value)

    for fmt in input_formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime()


def normalize_measurement_date(value: Any, policy: dict[str, Any] | None = None) -> str:
    """Normalize a measurement date into a configurable output format.

    Default output is YYYYMMDD.
    """
    policy = policy or {}
    output_format = policy.get("output_format", "%Y%m%d")
    input_formats = policy.get("input_formats", DEFAULT_DATE_INPUT_FORMATS)

    dt = _parse_datetime_with_formats(value, list(input_formats))
    if dt is not None:
        return dt.strftime(output_format)

    text = _as_clean_string(value)
    digits = re.sub(r"\D", "", text)
    if len(digits) == 8 and output_format == "%Y%m%d":
        return digits
    return text


def normalize_measurement_time(value: Any, policy: dict[str, Any] | None = None) -> str:
    """Normalize a measurement time into a configurable output format.

    Default output is HHMMSS. This fixes values such as 93425 -> 093425.
    """
    policy = policy or {}
    output_format = policy.get("output_format", "%H%M%S")
    input_formats = policy.get("input_formats", DEFAULT_TIME_INPUT_FORMATS)

    if isinstance(value, time):
        return value.strftime(output_format)

    dt = _parse_datetime_with_formats(value, list(input_formats))
    if dt is not None:
        return dt.strftime(output_format)

    text = _as_clean_string(value)
    digits = re.sub(r"\D", "", text)

    if not digits:
        if output_format == "%H%M%S":
            return "000000"
        return ""

    if output_format == "%H%M%S":
        if len(digits) > 6:
            digits = digits[-6:]
        return digits.zfill(6)

    if len(digits) <= 6:
        digits = digits.zfill(6)
        try:
            dt = datetime.strptime(digits, "%H%M%S")
            return dt.strftime(output_format)
        except ValueError:
            return text

    return text


def normalize_station_id(value: Any, policy: dict[str, Any] | None = None) -> str:
    """Normalize station_id according to configurable string transforms.

    Supported policy keys:
      - remove_prefixes: list[str]
      - add_prefix: str
      - uppercase: bool
      - strip: bool
      - zero_pad: int
    """
    policy = policy or {}
    text = _as_clean_string(value)

    if policy.get("strip", True):
        text = text.strip()

    if policy.get("uppercase", True):
        text = text.upper()

    for prefix in policy.get("remove_prefixes", []) or []:
        prefix_text = str(prefix)
        compare_text = text.upper() if policy.get("uppercase", True) else text
        compare_prefix = prefix_text.upper() if policy.get("uppercase", True) else prefix_text
        if compare_text.startswith(compare_prefix):
            text = text[len(prefix_text):]
            break

    if policy.get("digits_only", False):
        text = "".join(re.findall(r"\d+", text))

    zero_pad = policy.get("zero_pad")
    if zero_pad and text.isdigit():
        text = text.zfill(int(zero_pad))

    add_prefix = policy.get("add_prefix")
    if add_prefix and text and not text.startswith(str(add_prefix)):
        text = f"{add_prefix}{text}"

    return text


def build_station_code(station_id: Any, policy: dict[str, Any] | None = None) -> str:
    """Build a display/local station code from station_id.

    Default leaves the value unchanged. Configure prefix to create values like P11.
    """
    policy = policy or {}
    text = _as_clean_string(station_id)
    prefix = str(policy.get("prefix", ""))
    suffix = str(policy.get("suffix", ""))

    if policy.get("uppercase", True):
        text = text.upper()
        prefix = prefix.upper()
        suffix = suffix.upper()

    if prefix and not text.startswith(prefix):
        text = f"{prefix}{text}"
    if suffix and not text.endswith(suffix):
        text = f"{text}{suffix}"

    return text


def apply_metadata_policy(df: pd.DataFrame, policy: dict[str, Any] | None = None) -> pd.DataFrame:
    """Apply metadata normalization to canonical traceability columns.

    This is intentionally conservative: it only changes columns that already exist.
    """
    policy = policy or {}
    df = df.copy()

    station_id_policy = policy.get("station_id", {}) or {}
    station_code_policy = policy.get("station_code", {}) or {}
    date_policy = policy.get("measurement_date", {}) or {}
    time_policy = policy.get("measurement_time", {}) or {}

    if "station_id" in df.columns:
        df["station_id"] = df["station_id"].map(
            lambda value: normalize_station_id(value, station_id_policy)
        )

    if "station_code" in df.columns:
        df["station_code"] = df["station_code"].map(
            lambda value: build_station_code(value, station_code_policy)
        )
    elif station_code_policy.get("enabled", False) and "station_id" in df.columns:
        df["station_code"] = df["station_id"].map(
            lambda value: build_station_code(value, station_code_policy)
        )

    if "measurement_date" in df.columns:
        df["measurement_date"] = df["measurement_date"].map(
            lambda value: normalize_measurement_date(value, date_policy)
        )

    if "measurement_time" in df.columns:
        df["measurement_time"] = df["measurement_time"].map(
            lambda value: normalize_measurement_time(value, time_policy)
        )

    return df
