from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import yaml


@dataclass
class FlowTrackerParseResult:
    raw_groups: Dict[str, List[Dict[str, Any]]]
    extracted_meta: Dict[str, Any]


class FlowTrackerDISAdapter:
    """
    Robust adapter for FlowTracker .dis files in Spanish and English.

    Criteria:
    - Summary: everything before the St table.
    - Points: full St table, flat, no extras_json.
    - Output columns in English where possible.
    - No row deduplication during ingest.
    """

    POINTS_HEADER_MAP = {
        "St": "station",
        "Reloj": "clock",
        "Clock": "clock",
        "PtoAfo": "location_m",
        "Loc": "location_m",
        "Calado": "depth_m",
        "Depth": "depth_m",
        "Hie": "ice_depth_m",
        "IceD": "ice_depth_m",
        "%Calado": "percent_depth",
        "%Dep": "percent_depth",
        "CalMed": "measured_depth_m",
        "MeasD": "measured_depth_m",
        "No": "num_points",
        "FactCorr": "correction_factor",
        "Vel": "velocity_m_s",
        "Angle": "angle_deg",
        "MeanVel": "mean_velocity_m_s",
        "Area": "area_m2",
        "Caudal": "discharge_m3_s",
        "Flow": "discharge_m3_s",
        "%Q": "percent_discharge",
        "Q": "quality_flag",
        "Temp": "temperature_c",
        "SNR": "snr_db",
        "Spk": "spike",
        "Verr": "velocity_error",
    }

    SUMMARY_COMPATIBILITY_ALIASES = {
        "file_name": [
            "file_name",
            "filename",
            "nombre_del_fichero",
            "nombre_fichero",
            "nombre_de_fichero",
        ],
        "site_name": [
            "site_name",
            "station_name",
            "measurement_station_name",
            "nom_del_punto_de_aforo",
            "nombre_del_punto_de_aforo",
            "nombre_punto_aforo",
        ],
        "station_name": [
            "site_name",
            "station_name",
            "measurement_station_name",
            "nom_del_punto_de_aforo",
            "nombre_del_punto_de_aforo",
            "nombre_punto_aforo",
        ],
        "start_date_time": [
            "start_date_time",
            "start_date_and_time",
            "fecha_y_hora_de_inicio",
            "fecha_hora_inicio",
        ],
        "number_stations": [
            "number_stations",
            "number_estaciones",
            "number_verticals",
            "number_of_stations",
            "estaciones",
            "verticals",
        ],
    }

    def parse_file_strict(self, dis_path: str, spec_path: str) -> FlowTrackerParseResult:
        spec = self._load_spec(spec_path)

        preferred_encoding = spec.get("encoding")
        lines, detected_encoding = self._read_lines_auto(
            dis_path,
            preferred_encoding=preferred_encoding,
        )

        summary_raw, table_start_idx = self._parse_summary_block(lines, spec)
        summary = self._apply_summary_aliases(summary_raw, spec)
        summary = self._add_compatibility_summary_fields(summary, dis_path)

        summary["input_file"] = os.path.basename(dis_path)
        summary["input_path"] = os.path.abspath(dis_path)
        summary["detected_encoding"] = detected_encoding

        self._validate_summary(summary, spec, dis_path)

        points, cols, raw_header_line = self._parse_points_table_strict(
            lines=lines,
            start_idx=table_start_idx,
            spec=spec,
            dis_path=dis_path,
        )

        for row in points:
            row["input_file"] = os.path.basename(dis_path)
            row["input_path"] = os.path.abspath(dis_path)
            row["detected_encoding"] = detected_encoding
            row["raw_points_header_line"] = raw_header_line

        extracted_meta = self._extract_meta_strict(summary, spec, dis_path)

        raw_groups = {
            "Summary": [summary],
            "Points": points,
            "Sections": [],
            "Gates": [],
        }

        return FlowTrackerParseResult(
            raw_groups=raw_groups,
            extracted_meta=extracted_meta,
        )

    # ---------------- IO / spec ----------------

    def _load_spec(self, spec_path: str) -> Dict[str, Any]:
        with open(spec_path, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
        return loaded or {}

    def _read_lines_auto(
        self,
        path: str | Path,
        preferred_encoding: Optional[str] = None,
    ) -> Tuple[List[str], str]:
        encodings: List[str] = []

        if preferred_encoding:
            encodings.append(preferred_encoding)

        encodings.extend(["utf-8-sig", "utf-8", "cp1252", "latin-1"])

        for enc in encodings:
            try:
                with open(path, "r", encoding=enc) as f:
                    lines = [ln.rstrip("\n\r") for ln in f]
                return lines, enc
            except UnicodeDecodeError:
                continue

        with open(path, "r", encoding="latin-1", errors="replace") as f:
            lines = [ln.rstrip("\n\r") for ln in f]

        return lines, "latin-1-replace"

    # ---------------- Summary ----------------

    def _parse_summary_block(
        self,
        lines: List[str],
        spec: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], int]:
        summary: Dict[str, Any] = {}

        pt_legacy = spec.get("points_table", {}) or {}
        table_header_re = re.compile(pt_legacy.get("header_regex", r"^\s*St\s+"))
        header_variants = (spec.get("points", {}) or {}).get("header_variants") or []

        current_key: Optional[str] = None
        current_section: Optional[str] = None

        for i, ln in enumerate(lines):
            if self._is_points_header_line(ln, table_header_re, header_variants):
                return summary, i

            clean_ln = ln.strip("\ufeff")
            stripped = clean_ln.strip()

            if stripped == "":
                current_key = None
                continue

            section_norm = self._to_snake_case(stripped)

            if section_norm in {
                "discharge_uncertainty_iso",
                "incertidumbre_del_aforo_iso",
            }:
                current_section = "discharge_uncertainty_iso"
                summary[f"unparsed_summary_line_{i + 1}"] = stripped
                current_key = None
                continue

            if section_norm in {
                "discharge_uncertainty_statistical",
                "incertidumbre_del_aforo_estadistica",
            }:
                current_section = "discharge_uncertainty_statistical"
                summary[f"unparsed_summary_line_{i + 1}"] = stripped
                current_key = None
                continue

            if section_norm in {
                "automatic_quality_control_test_beamcheck",
                "control_automatico_de_calidad_beamcheck",
            }:
                current_section = "beamcheck"
                summary[f"unparsed_summary_line_{i + 1}"] = stripped
                current_key = None
                continue

            if current_section == "beamcheck":
                summary[f"unparsed_summary_line_{i + 1}"] = stripped
                continue

            parts = re.split(r"\s{2,}", clean_ln.strip(), maxsplit=1)

            if len(parts) == 1:
                if current_key:
                    self._append_value(summary, current_key, parts[0].strip())
                else:
                    summary[f"unparsed_summary_line_{i + 1}"] = parts[0].strip()
                continue

            raw_key, raw_value = parts[0].strip(), parts[1].strip()

            if raw_key == "":
                if current_key:
                    self._append_value(summary, current_key, raw_value)
                continue

            key_base = self._summary_key(raw_key)

            if current_section == "discharge_uncertainty_iso":
                key_base = f"discharge_uncertainty_iso_{key_base}"
            elif current_section == "discharge_uncertainty_statistical":
                key_base = f"discharge_uncertainty_statistical_{key_base}"

            final_key, final_value = self._parse_summary_value_with_units(
                key_base,
                raw_value,
            )

            current_key = final_key

            if final_key in summary:
                self._append_value(summary, final_key, final_value)
            else:
                summary[final_key] = final_value

        return summary, len(lines)

    def _summary_key(self, raw_key: str) -> str:
        key = self._to_snake_case(raw_key)

        aliases = {
            "number_stations": "number_stations",
            "stations": "number_stations",
            "num_stations": "number_stations",
            "serial_number": "serial_number",
            "serial_number_": "serial_number",
            "operator_s": "operators",
        }

        return aliases.get(key, key)

    def _parse_summary_value_with_units(
        self,
        key_base: str,
        raw_value: str,
    ) -> Tuple[str, Any]:
        value = str(raw_value).strip()

        m = re.match(
            r"^\s*(?P<num>[+-]?\d+(?:[.,]\d+)?)\s*"
            r"(?P<unit>%|m\^2|m\^3/s|m/s|m|dB|deg\s*C|sec)\s*$",
            value,
            flags=re.IGNORECASE,
        )

        if m:
            num = m.group("num").replace(",", ".")
            unit = m.group("unit")
            suffix = self._unit_to_suffix(unit)
            return f"{key_base}_{suffix}", num

        m = re.match(r"^\s*(?P<num>[+-]?\d+(?:[.,]\d+)?)%\s*$", value)
        if m:
            num = m.group("num").replace(",", ".")
            return f"{key_base}_percent", num

        return key_base, value

    def _unit_to_suffix(self, unit: str) -> str:
        unit_clean = unit.strip().lower().replace(" ", "")

        unit_map = {
            "%": "percent",
            "m": "m",
            "m^2": "m2",
            "m^3/s": "m3_s",
            "m/s": "m_s",
            "db": "dB",
            "degc": "degC",
            "sec": "sec",
        }

        return unit_map.get(unit_clean, self._to_snake_case(unit_clean))

    def _append_value(self, summary: Dict[str, Any], key: str, value: str) -> None:
        existing = summary.get(key)

        if existing is None:
            summary[key] = value
        elif isinstance(existing, list):
            existing.append(value)
        else:
            summary[key] = [existing, value]

    def _apply_summary_aliases(
        self,
        summary: Dict[str, Any],
        spec: Dict[str, Any],
    ) -> Dict[str, Any]:
        alias_map = (spec.get("summary", {}) or {}).get("key_aliases") or {}

        if not alias_map:
            return {
                self._to_snake_case(str(k)): v
                for k, v in summary.items()
            }

        reverse: Dict[str, str] = {}

        for canonical, aliases in alias_map.items():
            if canonical:
                reverse[self._norm_key(canonical)] = self._to_snake_case(canonical)

            if isinstance(aliases, list):
                for alias in aliases:
                    if alias:
                        reverse[self._norm_key(str(alias))] = self._to_snake_case(canonical)
            elif isinstance(aliases, str) and aliases:
                reverse[self._norm_key(aliases)] = self._to_snake_case(canonical)

        out: Dict[str, Any] = {}

        for key, value in summary.items():
            canonical_key = reverse.get(
                self._norm_key(str(key)),
                self._to_snake_case(str(key)),
            )

            if canonical_key in out:
                if isinstance(value, list):
                    for item in value:
                        self._append_value(out, canonical_key, str(item))
                else:
                    self._append_value(out, canonical_key, str(value))
            else:
                out[canonical_key] = value

        return out

    def _add_compatibility_summary_fields(
        self,
        summary: Dict[str, Any],
        dis_path: str | Path,
    ) -> Dict[str, Any]:
        summary = dict(summary)

        for canonical_key, candidates in self.SUMMARY_COMPATIBILITY_ALIASES.items():
            if summary.get(canonical_key):
                continue

            for candidate in candidates:
                candidate_key = self._to_snake_case(candidate)
                value = summary.get(candidate_key)

                if value not in (None, ""):
                    summary[canonical_key] = value
                    break

        if not summary.get("file_name"):
            summary["file_name"] = os.path.basename(dis_path)

        if not summary.get("start_date_time"):
            summary["start_date_time"] = self._extract_datetime(
                summary.get("start_date_and_time")
                or summary.get("fecha_y_hora_de_inicio")
                or ""
            )
        else:
            summary["start_date_time"] = self._extract_datetime(
                summary.get("start_date_time")
            )

        if not summary.get("station_name"):
            summary["station_name"] = (
                summary.get("site_name")
                or summary.get("nom_del_punto_de_aforo")
                or ""
            )

        if not summary.get("site_name"):
            summary["site_name"] = summary.get("station_name") or ""

        return summary

    def _extract_datetime(self, value: Any) -> str:
        text = str(value or "")

        m = re.search(r"\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}", text)
        if m:
            return m.group(0)

        m = re.search(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}", text)
        if m:
            return m.group(0).replace("-", "/")

        return text.strip()

    def _norm_key(self, value: str) -> str:
        value = value.strip().lower()
        value = value.replace("\t", " ")
        value = value.replace("_", " ")
        value = re.sub(r"[·•]", " ", value)
        value = re.sub(r"\s+", " ", value)
        value = value.replace(".", "")
        return value

    def _to_snake_case(self, value: str) -> str:
        value = str(value).strip()
        value = value.replace("\ufeff", "")

        replacements = {
            "#": "number",
            "%": "percent",
            "/": "_per_",
            "\\": "_",
            "-": "_",
            ".": "",
            "(": "",
            ")": "",
            "[": "",
            "]": "",
            ":": "",
            ",": "",
            "á": "a",
            "Á": "A",
            "é": "e",
            "É": "E",
            "í": "i",
            "Í": "I",
            "ó": "o",
            "Ó": "O",
            "ú": "u",
            "Ú": "U",
            "ñ": "n",
            "Ñ": "N",
        }

        for old, new in replacements.items():
            value = value.replace(old, new)

        value = re.sub(r"\s+", "_", value)
        value = re.sub(r"__+", "_", value)

        return value.strip("_").lower()

    def _validate_summary(
        self,
        summary: Dict[str, Any],
        spec: Dict[str, Any],
        dis_path: str,
    ) -> None:
        required_keys = (spec.get("summary", {}) or {}).get("required_keys", []) or []

        if not required_keys:
            return

        missing = [
            self._to_snake_case(key)
            for key in required_keys
            if self._to_snake_case(key) not in summary
        ]

        if missing:
            raise ValueError(
                "FlowTracker .dis format mismatch: missing required summary keys.\n"
                f"File: {dis_path}\n"
                f"Missing: {missing}\n"
                f"Available keys: {list(summary.keys())}"
            )

    # ---------------- Points ----------------

    def _is_points_header_line(
        self,
        line: str,
        legacy_header_re: re.Pattern,
        header_variants: List[Dict[str, Any]],
    ) -> bool:
        line = (line or "").strip()

        if not line:
            return False

        tokens = line.split()

        if tokens and tokens[0].strip() == "St":
            joined = " ".join(tokens).lower()

            indicators = [
                "reloj",
                "clock",
                "ptoafo",
                "loc",
                "calado",
                "depth",
                "caudal",
                "flow",
            ]

            if any(indicator in joined for indicator in indicators):
                return True

        if header_variants:
            low = line.lower()
            for header_variant in header_variants:
                tokens_all = header_variant.get("tokens_all") or []
                if tokens_all and all(str(token).lower() in low for token in tokens_all):
                    return True

        return bool(legacy_header_re.search(line))

    def _parse_points_table_strict(
        self,
        lines: List[str],
        start_idx: int,
        spec: Dict[str, Any],
        dis_path: str,
    ) -> Tuple[List[Dict[str, Any]], List[str], str]:
        pt_legacy = spec.get("points_table", {}) or {}

        header_re = re.compile(
            pt_legacy.get("header_regex", r"^\s*St\s+")
        )

        header_variants = (spec.get("points", {}) or {}).get("header_variants") or []

        units_startswith = pt_legacy.get("units_line_startswith", "(")

        data_row_re = re.compile(
            pt_legacy.get(
                "data_row_regex",
                r"^\s*\d+\s+\d{2}:\d{2}\b",
            )
        )

        header_idx = None

        for i in range(start_idx, min(start_idx + 80, len(lines))):
            if self._is_points_header_line(lines[i], header_re, header_variants):
                header_idx = i
                break

        if header_idx is None:
            raise ValueError(
                "FlowTracker .dis format mismatch: points header not found.\n"
                f"File: {dis_path}"
            )

        raw_header_line = lines[header_idx]
        raw_cols = re.split(r"\s+", raw_header_line.strip())
        cols = [self._normalize_points_column_name(col) for col in raw_cols]

        units_idx = self._find_units_line(
            lines=lines,
            header_idx=header_idx,
            units_startswith=units_startswith,
            dis_path=dis_path,
        )

        data_start = units_idx + 1

        points: List[Dict[str, Any]] = []
        started = False

        for k in range(data_start, len(lines)):
            raw_line = lines[k]
            line = raw_line.strip()

            if line == "":
                if started:
                    break
                continue

            if not data_row_re.search(line):
                if started:
                    break
                continue

            started = True
            tokens = re.split(r"\s+", line)

            if len(tokens) < len(cols):
                raise ValueError(
                    "FlowTracker .dis format mismatch: too few values in points row.\n"
                    f"File: {dis_path}\n"
                    f"Line number: {k + 1}\n"
                    f"Expected {len(cols)} columns: {cols}\n"
                    f"Found {len(tokens)} values: {tokens}\n"
                    f"Raw line: {raw_line}"
                )

            if len(tokens) > len(cols):
                tokens = tokens[:len(cols)]

            row = {
                column: token
                for column, token in zip(cols, tokens)
            }

            row["source_line_number"] = k + 1
            row["raw_source_line"] = raw_line

            points.append(row)

        if not points:
            raise ValueError(
                "FlowTracker .dis format mismatch: no points rows found.\n"
                f"File: {dis_path}"
            )

        return points, cols, raw_header_line

    def _normalize_points_column_name(self, col: str) -> str:
        if col in self.POINTS_HEADER_MAP:
            return self.POINTS_HEADER_MAP[col]

        return self._to_snake_case(col)

    def _find_units_line(
        self,
        lines: List[str],
        header_idx: int,
        units_startswith: str,
        dis_path: str,
    ) -> int:
        default_idx = header_idx + 1

        if (
            default_idx < len(lines)
            and lines[default_idx].strip().startswith(units_startswith)
        ):
            return default_idx

        for j in range(header_idx + 1, min(header_idx + 12, len(lines))):
            if lines[j].strip().startswith(units_startswith):
                return j

        raise ValueError(
            "FlowTracker .dis format mismatch: units line not found after points header.\n"
            f"File: {dis_path}\n"
            f"Header line: {lines[header_idx]}"
        )

    # ---------------- Meta ----------------

    def _extract_meta_strict(
        self,
        summary: Dict[str, Any],
        spec: Dict[str, Any],
        dis_path: str,
    ) -> Dict[str, Any]:
        extracted: Dict[str, Any] = {
            "source": "flowtracker",
            "input_file": os.path.basename(dis_path),
            "input_path": os.path.abspath(dis_path),
            "format_id": spec.get("format_id"),
            "format_version": spec.get("format_version"),
            "station_id": self._clean_file_name_as_station_id(
                summary.get("file_name") or os.path.basename(dis_path)
            ),
            "station_name": (
                summary.get("site_name")
                or summary.get("station_name")
                or ""
            ),
        }

        dt_value = (
            summary.get("start_date_time")
            or summary.get("start_date_and_time")
            or summary.get("fecha_y_hora_de_inicio")
            or ""
        )

        dt_value = self._extract_datetime(dt_value)

        m = re.search(
            r"(?P<date>\d{4}/\d{2}/\d{2})\s+(?P<time>\d{2}:\d{2}:\d{2})",
            str(dt_value),
        )

        if m:
            extracted["measurement_date"] = m.group("date").replace("/", "")
            extracted["measurement_time"] = m.group("time").replace(":", "")
        else:
            extracted["measurement_date"] = ""
            extracted["measurement_time"] = ""

        nv_raw = (
            summary.get("number_stations")
            or summary.get("number_estaciones")
            or summary.get("number_verticals")
            or summary.get("number_of_stations")
            or summary.get("estaciones")
            or summary.get("verticals")
        )

        m_verticals = re.search(r"\d+", str(nv_raw)) if nv_raw is not None else None
        extracted["n_verticals"] = int(m_verticals.group()) if m_verticals else None

        return extracted

    def _clean_file_name_as_station_id(self, value: Any) -> str:
        text = str(value or "").strip()

        if not text:
            return "UNKNOWN"

        text = Path(text).stem

        if text.upper().endswith(".TXT"):
            text = Path(text).stem

        text = re.sub(r"[^A-Za-z0-9_-]+", "_", text).strip("_")

        return text.upper() if text else "UNKNOWN"


def parse_flowtracker_dis(dis_path: str | Path, spec_path: str | Path | None = None):
    adapter = FlowTrackerDISAdapter()

    if spec_path is not None:
        result = adapter.parse_file_strict(str(dis_path), str(spec_path))
        summary_rows = result.raw_groups.get("Summary", [])
        points_rows = result.raw_groups.get("Points", [])

        summary = summary_rows[0] if summary_rows else {}
        points_df = pd.DataFrame(points_rows)

        return summary, points_df

    spec: Dict[str, Any] = {}

    lines, detected_encoding = adapter._read_lines_auto(dis_path)

    summary_raw, table_start_idx = adapter._parse_summary_block(lines, spec)
    summary = adapter._apply_summary_aliases(summary_raw, spec)
    summary = adapter._add_compatibility_summary_fields(summary, dis_path)

    summary = {
        key: _scalarize(value)
        for key, value in summary.items()
    }

    summary["input_file"] = os.path.basename(dis_path)
    summary["input_path"] = os.path.abspath(dis_path)
    summary["detected_encoding"] = detected_encoding

    points, cols, raw_header_line = adapter._parse_points_table_strict(
        lines=lines,
        start_idx=table_start_idx,
        spec=spec,
        dis_path=str(dis_path),
    )

    for row in points:
        row["input_file"] = os.path.basename(dis_path)
        row["input_path"] = os.path.abspath(dis_path)
        row["detected_encoding"] = detected_encoding
        row["raw_points_header_line"] = raw_header_line

    points_df = pd.DataFrame(points)

    return summary, points_df


def _scalarize(value: Any) -> Any:
    if isinstance(value, list):
        return " | ".join(str(item) for item in value if item is not None)
    return value