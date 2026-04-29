# normalizer.py
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from datetime import date, datetime, time


# -----------------------------
# Helpers
# -----------------------------
def _json_safe(obj):
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    return str(obj)


def _normalize_key(k: str) -> str:
    s = str(k).strip().lower()
    s = s.replace("\t", " ")
    s = s.replace("_", " ")
    s = re.sub(r"[#\.:;/\(\)\[\]\{\}]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _normalize_date_yyyymmdd(value: Any) -> str:
    if value is None:
        return ""

    s = str(value).strip()

    if s.endswith(".0"):
        s = s[:-2]

    digits = re.sub(r"\D", "", s)

    if len(digits) == 8:
        return digits

    return s


def _normalize_time_hhmmss(value: Any) -> str:
    """
    Normalize time to HHMMSS as a 6-character string.

    Examples:
      93425  -> 093425
      91500  -> 091500
      093425 -> 093425
      09:34:25 -> 093425
      "" -> 000000
    """
    if value is None:
        return "000000"

    if isinstance(value, time):
        return value.strftime("%H%M%S")

    if isinstance(value, datetime):
        return value.strftime("%H%M%S")

    s = str(value).strip()

    if s == "" or s.lower() in {"nan", "none", "null"}:
        return "000000"

    if s.endswith(".0"):
        s = s[:-2]

    digits = re.sub(r"\D", "", s)

    if digits == "":
        return "000000"

    if len(digits) > 6:
        digits = digits[-6:]

    return digits.zfill(6)


def _safe_str(x: Any) -> Optional[str]:
    if x is None:
        return None
    s = str(x).strip()
    return s if s else None


def _strip_units_keep_number(s: str) -> str:
    return re.sub(r"[^\d\.\-eE,]+", "", s)


def _safe_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, list) and x:
        x = x[0]
    if isinstance(x, (int, float)):
        return float(x)

    s = str(x).strip()

    if s == "" or s.lower() in {"nan", "none", "null"}:
        return None

    s = _strip_units_keep_number(s)

    if s.count(",") == 1 and s.count(".") == 0:
        s = s.replace(",", ".")

    try:
        return float(s)
    except Exception:
        return None


def _safe_int(x: Any) -> Optional[int]:
    f = _safe_float(x)
    if f is None:
        return None
    try:
        return int(round(f))
    except Exception:
        return None


def _cast_value(value: Any, target_type: str) -> Any:
    if target_type == "float":
        return _safe_float(value)
    if target_type == "int":
        return _safe_int(value)
    if target_type == "str":
        return _safe_str(value)
    return value


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=_json_safe)


def _build_measurement_id(
    source: str,
    station_id: str,
    date: str,
    time: str,
    run_id: str = "0",
) -> str:
    d = _normalize_date_yyyymmdd(date)
    t = _normalize_time_hhmmss(time)
    return f"{source}:{station_id}:{d}:{t}:{run_id}"


# -----------------------------
# Dataclass: metadata input
# -----------------------------
@dataclass
class SourceMeta:
    source: str
    station_id: str
    measurement_date: str  # YYYYMMDD
    measurement_time: str  # HHMMSS or ""
    timezone: str
    input_file: str
    input_path: str = ""
    run_id: str = "0"


# -----------------------------
# Normalizer
# -----------------------------
class Normalizer:
    """
    Normalize raw_groups -> canonical DataFrames using registry.yml.

    Important:
      - measurement_date is normalized to YYYYMMDD when possible.
      - measurement_time is always normalized to HHMMSS with 6 digits.
    """

    GROUPS = ["Summary", "Points", "Sections", "Gates"]

    def __init__(self, registry: Dict[str, Any]):
        self.registry = registry
        self.defaults = registry.get("defaults", {})
        self.core_fields = registry.get("core_fields", [])

        self.canon_dict = registry.get("canonical_dictionary", {})
        self.sources = registry.get("sources", {})
        self.derived_fields = registry.get("derived_fields", [])

    # -------------------------
    # Public API
    # -------------------------
    def normalize_measurement(
        self,
        raw_groups: Dict[str, List[Dict[str, Any]]],
        meta: SourceMeta,
    ) -> Dict[str, pd.DataFrame]:

        for g in self.GROUPS:
            raw_groups.setdefault(g, [])

        measurement_date = _normalize_date_yyyymmdd(meta.measurement_date)
        measurement_time = _normalize_time_hhmmss(meta.measurement_time)

        measurement_id = _build_measurement_id(
            meta.source,
            meta.station_id,
            measurement_date,
            measurement_time,
            meta.run_id,
        )

        normalized_meta = SourceMeta(
            source=meta.source,
            station_id=meta.station_id,
            measurement_date=measurement_date,
            measurement_time=measurement_time,
            timezone=meta.timezone,
            input_file=meta.input_file,
            input_path=meta.input_path,
            run_id=meta.run_id,
        )

        out: Dict[str, pd.DataFrame] = {}
        out["Summary"] = self._normalize_summary(
            raw_groups["Summary"],
            normalized_meta,
            measurement_id,
        )
        out["Points"] = self._normalize_group(
            "points",
            raw_groups["Points"],
            normalized_meta,
            measurement_id,
        )
        out["Sections"] = self._normalize_group(
            "sections",
            raw_groups["Sections"],
            normalized_meta,
            measurement_id,
        )
        out["Gates"] = self._normalize_group(
            "gates",
            raw_groups["Gates"],
            normalized_meta,
            measurement_id,
        )

        for g, df in out.items():
            if not df.empty:
                out[g] = self._apply_derived_fields(df)

        return out

    # -------------------------
    # Internals
    # -------------------------
    def _core_row(self, meta: SourceMeta, measurement_id: str) -> Dict[str, Any]:
        measurement_date = _normalize_date_yyyymmdd(meta.measurement_date)
        measurement_time = _normalize_time_hhmmss(meta.measurement_time)

        return {
            "schema_version": self.defaults.get("schema_version", "0.1"),
            "source": meta.source,
            "station_id": meta.station_id,
            "measurement_id": measurement_id,
            "measurement_date": measurement_date,
            "measurement_time": measurement_time,
            "timezone": meta.timezone or self.defaults.get("timezone", "America/Montevideo"),
            "input_file": meta.input_file,
            "input_path": meta.input_path,
        }

    def _source_cfg(self, source: str) -> Dict[str, Any]:
        if source not in self.sources:
            raise KeyError(f"Source '{source}' not found in registry.yml (sources.{source})")
        return self.sources[source]

    def _normalize_summary(
        self,
        raw_summary: List[Dict[str, Any]],
        meta: SourceMeta,
        measurement_id: str,
    ) -> pd.DataFrame:

        src_cfg = self._source_cfg(meta.source)
        mapping_cfg = src_cfg.get("mapping", {}).get("summary", {})
        mode = mapping_cfg.get("mode", "direct_key_match")

        core = self._core_row(meta, measurement_id)

        if mode == "pivot_long_to_wide":
            param_field = mapping_cfg.get("parameter_field", "Parameter")
            value_field = mapping_cfg.get("value_field", "Value")
            wide: Dict[str, Any] = {}

            for row in raw_summary:
                p = row.get(param_field)
                v = row.get(value_field)
                if p is None:
                    continue
                wide[str(p)] = v

            raw_dict = wide
        else:
            raw_dict: Dict[str, Any] = {}
            for row in raw_summary:
                raw_dict.update(row)

        explicit_fields = mapping_cfg.get("fields", {}) or {}

        canonical_row, extras = self._map_dict_to_canonical(
            group_key="summary",
            raw_dict=raw_dict,
            explicit_map=explicit_fields,
        )

        out_row = {**core, **canonical_row}
        out_row["extras_json"] = _json_dumps(extras) if extras else _json_dumps({})

        return pd.DataFrame([out_row])

    def _normalize_group(
        self,
        group_key: str,
        raw_rows: List[Dict[str, Any]],
        meta: SourceMeta,
        measurement_id: str,
    ) -> pd.DataFrame:

        src_cfg = self._source_cfg(meta.source)
        mapping_cfg = src_cfg.get("mapping", {}).get(group_key, {})
        mode = mapping_cfg.get("mode", "direct_key_match")

        if mode == "none":
            return pd.DataFrame(columns=self._expected_columns(group_key))

        core_base = self._core_row(meta, measurement_id)

        explicit_map = {}
        if "column_map" in mapping_cfg:
            explicit_map = mapping_cfg["column_map"]
        elif "column_aliases" in mapping_cfg:
            explicit_map = mapping_cfg["column_aliases"]

        out_rows: List[Dict[str, Any]] = []

        for raw in raw_rows:
            canonical_row, extras = self._map_dict_to_canonical(
                group_key=group_key,
                raw_dict=raw,
                explicit_map=explicit_map,
            )

            out_row = {**core_base, **canonical_row}
            out_row["extras_json"] = _json_dumps(extras) if extras else _json_dumps({})
            out_rows.append(out_row)

        if not out_rows:
            return pd.DataFrame(columns=self._expected_columns(group_key))

        return pd.DataFrame(out_rows)

    def _expected_columns(self, group_key: str) -> List[str]:
        canon = self.canon_dict.get(group_key, {})

        base = [
            "schema_version",
            "source",
            "station_id",
            "measurement_id",
            "measurement_date",
            "measurement_time",
            "timezone",
            "input_file",
            "input_path",
        ]

        return list(dict.fromkeys(base + list(canon.keys()) + ["extras_json"]))

    def _map_dict_to_canonical(
        self,
        group_key: str,
        raw_dict: Dict[str, Any],
        explicit_map: Dict[str, str],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:

        canon_spec = self.canon_dict.get(group_key, {}) or {}

        explicit_norm = {
            _normalize_key(k): v
            for k, v in (explicit_map or {}).items()
        }

        alias_index: Dict[str, str] = {}

        for canon_field, spec in canon_spec.items():
            for a in (spec.get("aliases") or []):
                alias_index[_normalize_key(a)] = canon_field

        canon_out: Dict[str, Any] = {}
        extras: Dict[str, Any] = {}

        for rk, rv in (raw_dict or {}).items():
            rk_norm = _normalize_key(rk)

            if rk_norm in explicit_norm:
                cf = explicit_norm[rk_norm]
            elif rk_norm in alias_index:
                cf = alias_index[rk_norm]
            else:
                extras[str(rk)] = rv
                continue

            if cf in canon_spec:
                target_type = canon_spec[cf].get("type", "str")
                new_val = _cast_value(rv, target_type)

                if cf in canon_out:
                    old_val = canon_out[cf]
                    if old_val is not None and not (
                        isinstance(old_val, float) and pd.isna(old_val)
                    ):
                        continue

                canon_out[cf] = new_val
            else:
                canon_out[cf] = rv

        return canon_out, extras

    def _apply_derived_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        for rule in self.derived_fields or []:
            required = rule.get("when_present", []) or []
            create = rule.get("create")
            formula = rule.get("formula")

            if not create or not formula:
                continue

            if not all(col in df.columns for col in required):
                continue

            mask = pd.Series(True, index=df.index)

            for col in required:
                mask &= df[col].notna()

            if not mask.any():
                continue

            local_ns = {c: df[c] for c in df.columns}

            try:
                computed = eval(formula, {"__builtins__": {}}, local_ns)

                if hasattr(computed, "loc"):
                    df.loc[mask, create] = computed.loc[mask]
                else:
                    df.loc[mask, create] = computed
            except Exception:
                continue

        return df