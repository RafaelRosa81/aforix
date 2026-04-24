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
    def parse_file_strict(self, dis_path: str, spec_path: str) -> FlowTrackerParseResult:
        spec = self._load_spec(spec_path)
        encoding = spec.get("encoding", "latin-1")
        lines = self._read_lines(dis_path, encoding=encoding)

        summary_raw, table_start_idx = self._parse_summary_block(lines, spec)

        # 1) Normalizamos las claves del summary (ES/EN) hacia claves canónicas
        summary = self._apply_summary_aliases(summary_raw, spec)

        self._validate_summary(summary, spec, dis_path)

        points, cols = self._parse_points_table_strict(lines, table_start_idx, spec, dis_path)
        extracted_meta = self._extract_meta_strict(summary, spec, dis_path)

        # Validación / corrección conocida: duplicados por St
        n_verticals = extracted_meta.get("n_verticals")
        if n_verticals is not None and len(points) != int(n_verticals):
            points_dedup = self._deduplicate_points_by_st(points)

            if len(points_dedup) == int(n_verticals):
                points = points_dedup
            else:
                raise ValueError(
                    "FlowTracker .dis format mismatch (unexpected number of points rows).\n"
                    f"File: {dis_path}\n"
                    f"Expected (#_Estaciones): {n_verticals}\n"
                    f"Found rows: {len(points)}\n"
                    f"Found rows after dedup: {len(points_dedup)}\n"
                    f"Columns: {cols}"
                )

        raw_groups = {"Summary": [summary], "Points": points, "Sections": [], "Gates": []}
        return FlowTrackerParseResult(raw_groups=raw_groups, extracted_meta=extracted_meta)

    # ---------------- IO / spec ----------------
    def _load_spec(self, spec_path: str) -> Dict[str, Any]:
        with open(spec_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _read_lines(self, path: str, encoding: str) -> List[str]:
        with open(path, "r", encoding=encoding, errors="replace") as f:
            return [ln.rstrip("\n\r") for ln in f]

    # ---------------- Summary ----------------
    def _parse_summary_block(self, lines: List[str], spec: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """
        Lee el bloque de summary como pares key/value usando separación por 2+ espacios.
        Se detiene cuando detecta la cabecera de la tabla de puntos.
        """
        summary: Dict[str, Any] = {}

        # Soporte viejo (spec points_table.header_regex)
        pt_legacy = spec.get("points_table", {}) or {}
        table_header_re = re.compile(pt_legacy.get("header_regex", r"^\s*St\s+Reloj\s+PtoAfo\s+Calado\b"))

        # Soporte nuevo (spec points.header_variants) — no dependemos del idioma
        # Si existe, la usamos para cortar el summary al inicio de la tabla.
        header_variants = (spec.get("points", {}) or {}).get("header_variants") or []

        current_key: Optional[str] = None
        for i, ln in enumerate(lines):
            if self._is_points_header_line(ln, table_header_re, header_variants):
                return summary, i

            if ln.strip() == "":
                current_key = None
                continue

            parts = re.split(r"\s{2,}", ln.strip("\ufeff"), maxsplit=1)
            if len(parts) == 1:
                if current_key:
                    self._append_value(summary, current_key, parts[0].strip())
                continue

            key, value = parts[0].strip(), parts[1].strip()
            if key == "":
                if current_key:
                    self._append_value(summary, current_key, value)
                continue

            current_key = key
            if key in summary:
                self._append_value(summary, key, value)
            else:
                summary[key] = value

        return summary, len(lines)

    def _append_value(self, summary: Dict[str, Any], key: str, value: str) -> None:
        existing = summary.get(key)
        if existing is None:
            summary[key] = value
        elif isinstance(existing, list):
            existing.append(value)
        else:
            summary[key] = [existing, value]

    def _apply_summary_aliases(self, summary: Dict[str, Any], spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convierte claves EN/variantes a claves canónicas (por ejemplo ES),
        usando spec.summary.key_aliases.

        Si no hay key_aliases, devuelve summary tal cual (compatibilidad).
        """
        alias_map = (spec.get("summary", {}) or {}).get("key_aliases") or {}
        if not alias_map:
            return summary

        # Construimos reverse lookup: alias -> canonical
        reverse: Dict[str, str] = {}
        for canonical, aliases in alias_map.items():
            if canonical:
                reverse[self._norm_key(canonical)] = canonical
            if isinstance(aliases, list):
                for a in aliases:
                    if a:
                        reverse[self._norm_key(str(a))] = canonical
            elif isinstance(aliases, str) and aliases:
                reverse[self._norm_key(aliases)] = canonical

        out: Dict[str, Any] = {}
        for k, v in summary.items():
            canon = reverse.get(self._norm_key(str(k)), str(k))
            # si ya existía, apilamos
            if canon in out:
                # preserve list nature
                if isinstance(v, list):
                    for item in v:
                        self._append_value(out, canon, str(item))
                else:
                    self._append_value(out, canon, str(v))
            else:
                out[canon] = v


        return out

    def _norm_key(self, s: str) -> str:
        # Normalización suave para comparar etiquetas: minúsculas, espacios/underscores equivalentes, puntos fuera
        s = s.strip().lower()
        s = s.replace("\t", " ")
        s = re.sub(r"[·•]", " ", s)
        s = s.replace("_", " ")
        s = re.sub(r"\s+", " ", s)
        s = s.replace(".", "")
        return s

    def _validate_summary(self, summary: Dict[str, Any], spec: Dict[str, Any], dis_path: str) -> None:
        req = (spec.get("summary", {}) or {}).get("required_keys", []) or []
        missing = [k for k in req if k not in summary]
        if missing:
            raise ValueError(
                "FlowTracker .dis format mismatch (missing required summary keys).\n"
                f"File: {dis_path}\nMissing: {missing}\n"
                f"Available keys: {list(summary.keys())}"
            )

    # ---------------- Points ----------------
    def _is_points_header_line(
        self,
        line: str,
        legacy_header_re: re.Pattern,
        header_variants: List[Dict[str, Any]],
    ) -> bool:
        """
        Detecta si una línea corresponde a la cabecera de la tabla de puntos.
        - Primero: header_variants (tokens_all) si existe en el spec.
        - Fallback: regex legacy points_table.header_regex (compatibilidad).
        """
        ln = (line or "").strip()
        if not ln:
            return False

        # 1) Nuevo: variantes por tokens (ES/EN)
        if header_variants:
            low = ln.lower()
            for hv in header_variants:
                tokens_all = hv.get("tokens_all") or []
                if tokens_all and all(str(t).lower() in low for t in tokens_all):
                    return True

        # 2) Viejo: regex hardcodeado / configurable
        return bool(legacy_header_re.search(line))

    def _parse_points_table_strict(
        self, lines: List[str], start_idx: int, spec: Dict[str, Any], dis_path: str
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Parse estricto de tabla de puntos.
        Soporta:
          - spec.points.header_variants (tokens_all) para encontrar cabecera ES/EN
          - spec.points_table.header_regex (legacy)
        """
        pt_legacy = spec.get("points_table", {}) or {}

        # Legacy regex (por defecto en español)
        header_re = re.compile(pt_legacy.get("header_regex", r"^\s*St\s+Reloj\s+PtoAfo\s+Calado\b"))

        # Nuevo: variantes ES/EN
        header_variants = (spec.get("points", {}) or {}).get("header_variants") or []

        units_startswith = pt_legacy.get("units_line_startswith", "(")
        expected_cols = pt_legacy.get("expected_columns", []) or []
        data_row_re = re.compile(pt_legacy.get("data_row_regex", r"^\s*\d{2}\s+\d{2}:\d{2}\b"))

        header_idx = None
        for i in range(start_idx, min(start_idx + 60, len(lines))):
            if self._is_points_header_line(lines[i], header_re, header_variants):
                header_idx = i
                break
        if header_idx is None:
            raise ValueError(f"FlowTracker .dis format mismatch (points header not found). File: {dis_path}")

        cols = lines[header_idx].strip().split()

        # Si el spec tiene columnas esperadas (legacy), las validamos
        if expected_cols and cols != expected_cols:
            raise ValueError(
                "FlowTracker .dis format mismatch (unexpected points columns).\n"
                f"File: {dis_path}\nExpected: {expected_cols}\nFound: {cols}"
            )

        # Units line (normalmente la fila siguiente, pero buscamos en un rango)
        units_idx = header_idx + 1
        if units_idx >= len(lines) or not lines[units_idx].strip().startswith(units_startswith):
            found = None
            for j in range(header_idx + 1, min(header_idx + 10, len(lines))):
                if lines[j].strip().startswith(units_startswith):
                    found = j
                    break
            if found is None:
                raise ValueError(f"FlowTracker .dis format mismatch (units line not found). File: {dis_path}")
            units_idx = found

        data_start = units_idx + 1
        points: List[Dict[str, Any]] = []
        started = False

        for k in range(data_start, len(lines)):
            ln = lines[k].strip()
            if ln == "":
                continue

            if not data_row_re.search(ln):
                if started:
                    break
                continue

            started = True
            tokens = ln.split()
            if len(tokens) < len(cols):
                raise ValueError(
                    "FlowTracker .dis format mismatch (too few columns in points row).\n"
                    f"File: {dis_path}\nLine: {lines[k]}"
                )
            if len(tokens) > len(cols):
                tokens = tokens[: len(cols) - 1] + [" ".join(tokens[len(cols) - 1 :])]

            points.append({c: t for c, t in zip(cols, tokens)})

        if not points:
            raise ValueError(f"FlowTracker .dis format mismatch (no points rows). File: {dis_path}")

        return points, cols

    def _to_float(self, s: Any) -> Optional[float]:
        if s is None:
            return None
        try:
            return float(str(s).replace(",", "."))
        except Exception:
            return None

    def _deduplicate_points_by_st(self, points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Dedup por 'St' eligiendo la fila “mejor”.
        Regla: preferir la fila con mayor |Caudal|, luego mayor Area, luego FactCorr != 0.
        Esto elimina filas típicas con FactCorr=0.00 y Area/Caudal=0.
        """
        by_st: Dict[str, List[Dict[str, Any]]] = {}
        for r in points:
            st = str(r.get("St", "")).strip()
            by_st.setdefault(st, []).append(r)

        out: List[Dict[str, Any]] = []
        for st, rows in by_st.items():
            if len(rows) == 1:
                out.append(rows[0])
                continue

            def score(row: Dict[str, Any]) -> tuple:
                q = self._to_float(row.get("Caudal"))
                a = self._to_float(row.get("Area"))
                fc = self._to_float(row.get("FactCorr"))
                return (abs(q or 0.0), a or 0.0, 1 if (fc is not None and fc != 0.0) else 0)

            best = sorted(rows, key=score, reverse=True)[0]
            out.append(best)

        def st_key(r: Dict[str, Any]) -> int:
            try:
                return int(str(r.get("St", "0")).strip())
            except Exception:
                return 10**9

        return sorted(out, key=st_key)

    # ---------------- Meta ----------------
    def _extract_meta_strict(self, summary: Dict[str, Any], spec: Dict[str, Any], dis_path: str) -> Dict[str, Any]:
        extracted: Dict[str, Any] = {
            "source": "flowtracker",
            "input_file": os.path.basename(dis_path),
            "input_path": os.path.abspath(dis_path),
            "format_id": spec.get("format_id"),
            "format_version": spec.get("format_version"),
        }

        st_key = (spec.get("station", {}) or {}).get("from_summary_key", "Nom._del_punto_de_aforo")
        extracted["station_name"] = summary.get(st_key, "")

        dt_cfg = spec.get("datetime", {}) or {}
        dt_key = dt_cfg.get("from_summary_key", "Fecha_y_hora_de_inicio")
        dt_val = summary.get(dt_key, "")
        pattern = dt_cfg.get("pattern", r"(?P<date>\d{4}/\d{2}/\d{2})\s+(?P<time>\d{2}:\d{2}:\d{2})")

        m = re.search(pattern, str(dt_val))
        if not m:
            raise ValueError(
                "FlowTracker .dis format mismatch (cannot parse datetime).\n"
                f"File: {dis_path}\nValue: {dt_val}\nPattern: {pattern}"
            )

        date_str = m.group("date") if "date" in m.groupdict() else m.group(1)
        time_str = m.group("time") if "time" in m.groupdict() else m.group(2)

        extracted["measurement_date"] = date_str.replace("/", "")
        extracted["measurement_time"] = time_str.replace(":", "")

        # n verticals: ahora depende de que ya hayamos mapeado aliases a "#_Estaciones"
        nv_raw = summary.get("#_Estaciones")
        m2 = re.search(r"\d+", str(nv_raw))
        extracted["n_verticals"] = int(m2.group()) if m2 else None

        return extracted
