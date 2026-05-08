from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aforix.metadata import (
    normalize_measurement_date,
    normalize_measurement_time,
    normalize_station_id,
)
from aforix.ingest.metadata import clean_station_name


@dataclass(frozen=True)
class MetadataExtractionContext:
    """Context available to ingest metadata extraction policies."""

    raw_fields: dict[str, Any]
    source_path: Path


_EMPTY_STRINGS = {"", "nan", "none", "null", "nat", "<na>"}


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    return str(value).strip().lower() in _EMPTY_STRINGS


def _as_text(value: Any) -> str:
    if _is_empty(value):
        return ""
    return str(value).strip()


def _regex_value(pattern: str, text: str) -> str:
    match = re.search(pattern, text)
    if not match:
        return ""

    if "value" in match.groupdict():
        return match.group("value")

    if match.groups():
        return match.group(1)

    return match.group(0)


def _extract_from_source(
    source_spec: dict[str, Any],
    *,
    context: MetadataExtractionContext,
) -> str:
    source_type = str(source_spec.get("type", "raw_field"))

    if source_type == "raw_field":
        key = source_spec.get("key")
        if not key:
            raise ValueError("raw_field source requires 'key'.")
        return _as_text(context.raw_fields.get(str(key)))

    if source_type == "filename_regex":
        pattern = source_spec.get("pattern")
        if not pattern:
            raise ValueError("filename_regex source requires 'pattern'.")
        return _regex_value(str(pattern), context.source_path.name)

    if source_type == "path_regex":
        pattern = source_spec.get("pattern")
        if not pattern:
            raise ValueError("path_regex source requires 'pattern'.")
        return _regex_value(str(pattern), str(context.source_path))

    if source_type == "constant":
        return _as_text(source_spec.get("value"))

    raise ValueError(f"Unsupported metadata source type: {source_type}")


def _first_non_empty(
    sources: list[dict[str, Any]],
    *,
    context: MetadataExtractionContext,
) -> str:
    for source_spec in sources:
        value = _extract_from_source(source_spec, context=context)
        if not _is_empty(value):
            return value
    return ""


def _apply_string_transforms(value: str, transforms: list[Any]) -> str:
    text = _as_text(value)

    for transform in transforms or []:
        if isinstance(transform, str):
            name = transform
            arg = None
        elif isinstance(transform, dict):
            name = str(transform.get("name", ""))
            arg = transform.get("value")
        else:
            raise ValueError(f"Invalid metadata transform: {transform!r}")

        if name == "strip":
            text = text.strip()
        elif name == "uppercase":
            text = text.upper()
        elif name == "lowercase":
            text = text.lower()
        elif name == "remove_prefix":
            prefix = str(arg or "")
            if text.upper().startswith(prefix.upper()):
                text = text[len(prefix):]
        elif name == "digits_only":
            text = "".join(re.findall(r"\d+", text))
        elif name == "zero_pad":
            if text.isdigit():
                text = text.zfill(int(arg))
        else:
            raise ValueError(f"Unsupported metadata transform: {name}")

    return text


def extract_metadata_field(
    field_name: str,
    field_policy: dict[str, Any],
    *,
    context: MetadataExtractionContext,
) -> str:
    """Extract a single metadata field according to a configurable policy."""

    sources = field_policy.get("sources", [])
    if not isinstance(sources, list):
        raise ValueError(f"metadata_policy.{field_name}.sources must be a list.")

    strategy = str(field_policy.get("strategy", "first_non_empty"))

    if strategy != "first_non_empty":
        raise ValueError(
            f"Unsupported metadata extraction strategy for {field_name}: {strategy}"
        )

    value = _first_non_empty(sources, context=context)

    transforms = field_policy.get("transforms", []) or []
    value = _apply_string_transforms(value, transforms)

    if field_name == "station_id":
        value = normalize_station_id(
            value,
            field_policy.get("normalize", {}) or {},
        )
    elif field_name == "station_name":
        value = clean_station_name(value) or ""
    elif field_name == "measurement_date":
        value = normalize_measurement_date(
            value,
            field_policy.get("normalize", {}) or {},
        )
    elif field_name == "measurement_time":
        value = normalize_measurement_time(
            value,
            field_policy.get("normalize", {}) or {},
        )

    return value


def extract_metadata(
    policy: dict[str, Any] | None,
    *,
    context: MetadataExtractionContext,
) -> dict[str, str]:
    """Extract configured metadata fields for an ingest parser.

    Missing fields are returned as empty strings; callers can keep their existing
    fallback behavior while progressively adopting this engine.
    """

    policy = policy or {}
    out: dict[str, str] = {}

    for field_name in [
        "station_id",
        "station_name",
        "measurement_date",
        "measurement_time",
    ]:
        field_policy = policy.get(field_name)
        if not field_policy:
            out[field_name] = ""
            continue
        if not isinstance(field_policy, dict):
            raise ValueError(f"metadata_policy.{field_name} must be a dictionary.")

        out[field_name] = extract_metadata_field(
            field_name,
            field_policy,
            context=context,
        )

    return out
