from __future__ import annotations

import re
from datetime import date, datetime, time
from typing import Any

import pandas as pd


DEFAULT_DATE_INPUT_FORMATS = [
    "%Y%m%d", "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y",
    "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S",
]
DEFAULT_TIME_INPUT_FORMATS = [
    "%H%M%S", "%H:%M:%S", "%H:%M", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S",
    "%m/%d/%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S",
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
    return text[:-2] if text.endswith(".0") else text


def canonical_station_id(value: Any) -> str:
    """Return the canonical Aforix station id.

    Legacy station codes P1..P999 are mapped into the 7000 namespace
    (P1 -> 7001, P71 -> 7071). Canonical 7xxx ids are preserved.
    Other numeric identifiers are preserved to avoid silently remapping
    unrelated station namespaces.
    """
    text = _as_clean_string(value).upper()
    if not text:
        return ""

    legacy = re.fullmatch(r"P\s*(\d{1,3})", text)
    if legacy:
        return str(7000 + int(legacy.group(1)))

    if re.fullmatch(r"7\d{3}", text):
        return text

    if re.fullmatch(r"\d+", text):
        return str(int(text))

    return text


def _parse_datetime_with_formats(value: Any, input_formats: list[str]) -> datetime | None:
    if _is_empty(value): return None
    if isinstance(value, datetime): return value
    if isinstance(value, date) and not isinstance(value, datetime): return datetime.combine(value, time.min)
    if isinstance(value, time): return datetime.combine(date.today(), value)
    text = _as_clean_string(value)
    for fmt in input_formats:
        try: return datetime.strptime(text, fmt)
        except ValueError: continue
    parsed = pd.to_datetime(text, errors="coerce")
    return None if pd.isna(parsed) else parsed.to_pydatetime()


def normalize_measurement_date(value: Any, policy: dict[str, Any] | None = None) -> str:
    policy = policy or {}
    output_format = policy.get("output_format", "%Y%m%d")
    dt = _parse_datetime_with_formats(value, list(policy.get("input_formats", DEFAULT_DATE_INPUT_FORMATS)))
    if dt is not None: return dt.strftime(output_format)
    text = _as_clean_string(value); digits = re.sub(r"\D", "", text)
    return digits if len(digits) == 8 and output_format == "%Y%m%d" else text


def normalize_measurement_time(value: Any, policy: dict[str, Any] | None = None) -> str:
    policy = policy or {}; output_format = policy.get("output_format", "%H%M%S")
    if isinstance(value, time): return value.strftime(output_format)
    dt = _parse_datetime_with_formats(value, list(policy.get("input_formats", DEFAULT_TIME_INPUT_FORMATS)))
    if dt is not None: return dt.strftime(output_format)
    text = _as_clean_string(value); digits = re.sub(r"\D", "", text)
    if not digits: return "000000" if output_format == "%H%M%S" else ""
    if output_format == "%H%M%S": return digits[-6:].zfill(6)
    if len(digits) <= 6:
        try: return datetime.strptime(digits.zfill(6), "%H%M%S").strftime(output_format)
        except ValueError: return text
    return text


def normalize_station_id(value: Any, policy: dict[str, Any] | None = None) -> str:
    policy = policy or {}; text = _as_clean_string(value)
    if policy.get("canonical", False):
        return canonical_station_id(text)
    if policy.get("strip", True): text = text.strip()
    if policy.get("uppercase", True): text = text.upper()
    for prefix in policy.get("remove_prefixes", []) or []:
        p = str(prefix); compare = text.upper() if policy.get("uppercase", True) else text
        cp = p.upper() if policy.get("uppercase", True) else p
        if compare.startswith(cp): text = text[len(p):]; break
    if policy.get("digits_only", False): text = "".join(re.findall(r"\d+", text))
    zero_pad = policy.get("zero_pad")
    if zero_pad and text.isdigit(): text = text.zfill(int(zero_pad))
    add_prefix = policy.get("add_prefix")
    if add_prefix and text and not text.startswith(str(add_prefix)): text = f"{add_prefix}{text}"
    return text


def build_station_code(station_id: Any, policy: dict[str, Any] | None = None) -> str:
    policy = policy or {}; text = _as_clean_string(station_id)
    prefix = str(policy.get("prefix", "")); suffix = str(policy.get("suffix", ""))
    if policy.get("uppercase", True): text, prefix, suffix = text.upper(), prefix.upper(), suffix.upper()
    if prefix and text and not text.startswith(prefix): text = f"{prefix}{text}"
    if suffix and text and not text.endswith(suffix): text = f"{text}{suffix}"
    return text


def apply_metadata_policy(df: pd.DataFrame, policy: dict[str, Any] | None = None) -> pd.DataFrame:
    policy = policy or {}; df = df.copy()
    station_id_policy = policy.get("station_id", {}) or {}; station_code_policy = policy.get("station_code", {}) or {}
    if "station_id" in df.columns: df["station_id"] = df["station_id"].map(lambda v: normalize_station_id(v, station_id_policy))
    if station_code_policy.get("enabled", False) and "station_id" in df.columns:
        df["station_code"] = df["station_id"].map(lambda v: build_station_code(v, station_code_policy))
    elif "station_code" in df.columns: df["station_code"] = df["station_code"].map(lambda v: build_station_code(v, station_code_policy))
    if "measurement_date" in df.columns: df["measurement_date"] = df["measurement_date"].map(lambda v: normalize_measurement_date(v, policy.get("measurement_date", {}) or {}))
    if "measurement_time" in df.columns: df["measurement_time"] = df["measurement_time"].map(lambda v: normalize_measurement_time(v, policy.get("measurement_time", {}) or {}))
    return df
