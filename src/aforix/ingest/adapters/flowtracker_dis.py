from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import yaml


@dataclass
class FlowTrackerParseResult:
    raw_groups: Dict[str, List[Dict[str, Any]]]
    extracted_meta: Dict[str, Any]


class FlowTrackerDISAdapter:
    """
    Adapter robusto para archivos FlowTracker .dis en español e inglés.

    Criterio:
    - Summary: todo lo anterior a la tabla St.
    - Points: toda la tabla St, plana, sin extras_json.
    - Columnas resultantes en inglés.
    - No deduplicar filas durante ingest.
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

    def parse_file_strict(self, dis_path: str, spec_path: str) -> FlowTrackerParseResult:
        spec = self._load_spec(spec_path)

        preferred_encoding = spec.get("encoding")
        lines, detected_encoding = self._read_lines_auto(
            dis_path,
            preferred_encoding=preferred_encoding,
        )

        summary_raw, table_start_idx = self._parse_summary_block(lines, spec)
        summary = self._apply_summary_aliases(summary_raw, spec)

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
            return yaml.safe_load(f)

    def _read_lines_auto(
        self,
        path: str,
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

            # Section headers
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
                "control_automatico_de_calidad_beamcheck",
            }:
                current_section = "beamcheck"
                summary[f"unparsed_summary_line_{i + 1}"] = stripped
                current_key = None
                continue

            # BeamCheck / final unstructured lines: keep as unparsed
            if current_section == "beamcheck":
                summary[f"unparsed_summary_line_{i + 1}"] = stripped
                continue

            parts = re.split(r"\s{2,}", clean_ln.strip(), maxsplit=1)

            # Continuation line, e.g. Boundary_Condition_(Bnd)
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

            # Build key, section-aware
            key_base = self._summary_key(raw_key)

            if current_section == "discharge_uncertainty_iso":
                key_base = f"discharge_uncertainty_iso_{key_base}"
            elif current_section == "discharge_uncertainty_statistical":
                key_base = f"discharge_uncertainty_statistical_{key_base}"

            final_key, final_value = self._parse_summary_value_with_units(key_base, raw_value)

            current_key = final_key

            if final_key in summary:
                self._append_value(summary, final_key, final_value)
            else:
                summary[final_key] = final_value

        return summary, len(lines)


    def _summary_key(self, raw_key: str) -> str:
        """
        Convert raw FlowTracker summary labels to readable snake_case.
        """
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


    def _parse_summary_value_with_units(self, key_base: str, raw_value: str) -> Tuple[str, Any]:
        """
        If value has units, move units to header and keep numeric value in cell.

        Examples:
          total_width + '5.600 m'      -> total_width_m = 5.600
          mean_temp + '21.85 deg C'    -> mean_temp_degC = 21.85
          mean_snr + '29.2 dB'         -> mean_snr_dB = 29.2
          uncertainty + '4.8 %'        -> ..._percent = 4.8
        """

        value = str(raw_value).strip()

        # Numeric + unit
        m = re.match(
            r"^\s*(?P<num>[+-]?\d+(?:[.,]\d+)?)\s*(?P<unit>%|m\^2|m\^3/s|m/s|m|dB|deg\s*C|sec)\s*$",
            value,
            flags=re.IGNORECASE,
        )

        if m:
            num = m.group("num").replace(",", ".")
            unit = m.group("unit")
            suffix = self._unit_to_suffix(unit)
            return f"{key_base}_{suffix}", num

        # Percent without space can appear, e.g. 0.0%
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
                for a in aliases:
                    if a:
                        reverse[self._norm_key(str(a))] = self._to_snake_case(canonical)
            elif isinstance(aliases, str) and aliases:
                reverse[self._norm_key(aliases)] = self._to_snake_case(canonical)

        out: Dict[str, Any] = {}

        for k, v in summary.items():
            canon = reverse.get(
                self._norm_key(str(k)),
                self._to_snake_case(str(k)),
            )

            if canon in out:
                if isinstance(v, list):
                    for item in v:
                        self._append_value(out, canon, str(item))
                else:
                    self._append_value(out, canon, str(v))
            else:
                out[canon] = v

        return out

    def _norm_key(self, s: str) -> str:
        s = s.strip().lower()
        s = s.replace("\t", " ")
        s = s.replace("_", " ")
        s = re.sub(r"[·•]", " ", s)
        s = re.sub(r"\s+", " ", s)
        s = s.replace(".", "")
        return s

    def _to_snake_case(self, s: str) -> str:
        s = str(s).strip()
        s = s.replace("\ufeff", "")

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
            s = s.replace(old, new)

        s = re.sub(r"\s+", "_", s)
        s = re.sub(r"__+", "_", s)

        return s.strip("_").lower()

    def _validate_summary(
        self,
        summary: Dict[str, Any],
        spec: Dict[str, Any],
        dis_path: str,
    ) -> None:

        req = (spec.get("summary", {}) or {}).get("required_keys", []) or []

        if not req:
            return

        missing = [
            self._to_snake_case(k)
            for k in req
            if self._to_snake_case(k) not in summary
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

        ln = (line or "").strip()

        if not ln:
            return False

        tokens = ln.split()

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

            if any(x in joined for x in indicators):
                return True

        if header_variants:
            low = ln.lower()
            for hv in header_variants:
                tokens_all = hv.get("tokens_all") or []
                if tokens_all and all(str(t).lower() in low for t in tokens_all):
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
        cols = [self._normalize_points_column_name(c) for c in raw_cols]

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
            ln_original = lines[k]
            ln = ln_original.strip()

            if ln == "":
                if started:
                    break
                continue

            if not data_row_re.search(ln):
                if started:
                    break
                continue

            started = True

            tokens = re.split(r"\s+", ln)

            if len(tokens) < len(cols):
                raise ValueError(
                    "FlowTracker .dis format mismatch: too few values in points row.\n"
                    f"File: {dis_path}\n"
                    f"Line number: {k + 1}\n"
                    f"Expected {len(cols)} columns: {cols}\n"
                    f"Found {len(tokens)} values: {tokens}\n"
                    f"Raw line: {ln_original}"
                )

            if len(tokens) > len(cols):
                tokens = tokens[:len(cols)]

            row = {
                c: t
                for c, t in zip(cols, tokens)
            }

            row["source_line_number"] = k + 1
            row["raw_source_line"] = ln_original

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
        }

        station_cfg = spec.get("station", {}) or {}
        st_key = self._to_snake_case(
            station_cfg.get("from_summary_key", "station_name")
        )

        extracted["station_name"] = (
            summary.get(st_key)
            or summary.get("nom_del_punto_de_aforo")
            or summary.get("station_name")
            or summary.get("measurement_station_name")
            or ""
        )

        dt_cfg = spec.get("datetime", {}) or {}
        dt_key = self._to_snake_case(
            dt_cfg.get("from_summary_key", "start_date_time")
        )

        dt_val = (
            summary.get(dt_key)
            or summary.get("fecha_y_hora_de_inicio")
            or summary.get("start_date_and_time")
            or summary.get("start_date_time")
            or ""
        )

        pattern = dt_cfg.get(
            "pattern",
            r"(?P<date>\d{4}/\d{2}/\d{2})\s+(?P<time>\d{2}:\d{2}:\d{2})",
        )

        m = re.search(pattern, str(dt_val))

        if m:
            date_str = m.group("date") if "date" in m.groupdict() else m.group(1)
            time_str = m.group("time") if "time" in m.groupdict() else m.group(2)

            extracted["measurement_date"] = date_str.replace("/", "").replace("-", "")
            extracted["measurement_time"] = time_str.replace(":", "")
        else:
            extracted["measurement_date"] = ""
            extracted["measurement_time"] = ""

        nv_raw = (
            summary.get("number_estaciones")
            or summary.get("number_verticals")
            or summary.get("number_of_stations")
            or summary.get("number_stations")
            or summary.get("estaciones")
            or summary.get("verticals")
        )

        m2 = re.search(r"\d+", str(nv_raw)) if nv_raw is not None else None
        extracted["n_verticals"] = int(m2.group()) if m2 else None

        return extracted
        

def parse_flowtracker_dis(dis_path: str, spec_path: str | None = None):
    import pandas as pd

    def scalarize(value):
        if isinstance(value, list):
            return " | ".join(str(v) for v in value if v is not None)
        return value

    spec = {}
    adapter = FlowTrackerDISAdapter()

    lines, detected_encoding = adapter._read_lines_auto(dis_path)

    summary_raw, table_start_idx = adapter._parse_summary_block(lines, spec)
    summary = adapter._apply_summary_aliases(summary_raw, spec)

    # Convert lists to strings for compatibility with old pipeline
    summary = {k: scalarize(v) for k, v in summary.items()}

    # Compatibility aliases expected by current aforix pipeline
    def extract_datetime(value):
        text = str(value or "")
        m = re.search(r"\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}", text)
        if m:
            return m.group(0)

        m = re.search(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}", text)
        if m:
            return m.group(0).replace("-", "/")

        return text

    summary["start_date_time"] = extract_datetime(summary.get("start_date_time"))
    if "start_date_time" not in summary or not summary["start_date_time"]:
        summary["start_date_time"] = (
            summary.get("fecha_y_hora_de_inicio")
            or summary.get("start_date_and_time")
            or ""
        )
    
    summary["start_date_time"] = extract_datetime(summary.get("start_date_time"))

    if "station_name" not in summary or not summary["station_name"]:
        summary["station_name"] = (
            summary.get("nom_del_punto_de_aforo")
            or summary.get("station_name")
            or ""
        )

    if "number_stations" not in summary or not summary["number_stations"]:
        summary["number_stations"] = (
            summary.get("number_estaciones")
            or summary.get("number_verticals")
            or summary.get("estaciones")
            or ""
        )

    summary["input_file"] = os.path.basename(dis_path)
    summary["input_path"] = os.path.abspath(dis_path)
    summary["detected_encoding"] = detected_encoding

    points, cols, raw_header_line = adapter._parse_points_table_strict(
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

    points_df = pd.DataFrame(points)

    return summary, points_df