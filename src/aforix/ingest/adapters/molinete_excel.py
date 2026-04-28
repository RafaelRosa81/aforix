from __future__ import annotations

import os
import re
import json
import datetime as dt
from dataclasses import dataclass
from typing import Any, Dict, Optional, List, Tuple

import pandas as pd


@dataclass
class ParseResult:
    extracted_meta: Dict[str, Any]
    raw_groups: Dict[str, pd.DataFrame]


class MolineteExcelFormatMismatch(RuntimeError):
    pass


class MolineteExcelAdapter:
    DEFAULT_SHEET_NAME = "CALCULO"

    POINTS_START_OFFSET = 3
    MAX_REV_VALUES = 3
    MAX_VEL_POINT_VALUES = 3

    def parse_file_strict(self, file_path: str, sheet_name: Optional[str] = None) -> ParseResult:
        ext = os.path.splitext(file_path)[1].lower()

        if ext not in [".xlsx", ".xls"]:
            raise MolineteExcelFormatMismatch(f"Unsupported file extension: {ext}")

        df, chosen_sheet = self._read_sheet_auto(file_path, sheet_name=sheet_name)

        station_id = (
            self._clean_station_id(self._value_right_of_label(df, "NOMBRE"))
            or self._infer_station_id(file_path)
        )

        measurement_date = self._to_date(self._value_right_of_label(df, "FECHA"))
        if measurement_date is None:
            measurement_date = self._infer_date_from_path_or_filename(file_path)

        if measurement_date is None:
            raise MolineteExcelFormatMismatch("Could not determine measurement_date.")

        start_time = self._to_time(self._value_right_of_label(df, "Hora Ini"))
        end_time = self._to_time(self._value_right_of_label(df, "Hora Fin"))
        measurement_time = start_time or dt.time(0, 0, 0)

        points_df = self._parse_points(
            df=df,
            station_id=station_id,
            measurement_date=measurement_date.strftime("%Y-%m-%d"),
            measurement_time=measurement_time.strftime("%H:%M:%S"),
            raw_source_file=os.path.basename(file_path),
            raw_sheet_name=chosen_sheet,
        )

        summary_df = self._parse_summary(
            df=df,
            file_path=file_path,
            station_id=station_id,
            measurement_date=measurement_date,
            measurement_time=measurement_time,
            start_time=start_time,
            end_time=end_time,
            raw_source_file=os.path.basename(file_path),
            raw_sheet_name=chosen_sheet,
            points_df=points_df,
        )

        extracted_meta = {
            "station_id": station_id,
            "measurement_date": measurement_date.strftime("%Y-%m-%d"),
            "measurement_time": measurement_time.strftime("%H:%M:%S"),
        }

        return ParseResult(
            extracted_meta=extracted_meta,
            raw_groups={
                "Summary": summary_df,
                "Points": points_df,
            },
        )

    # ------------------------------------------------------------------
    # Excel reading
    # ------------------------------------------------------------------
    def _read_sheet_auto(self, file_path: str, sheet_name: Optional[str] = None) -> Tuple[pd.DataFrame, str]:
        ext = os.path.splitext(file_path)[1].lower()
        engine = "xlrd" if ext == ".xls" else "openpyxl"

        xls = pd.ExcelFile(file_path, engine=engine)
        sheet_names = xls.sheet_names

        candidate_sheets: List[str] = []

        if sheet_name and sheet_name in sheet_names:
            candidate_sheets.append(sheet_name)

        if self.DEFAULT_SHEET_NAME in sheet_names and self.DEFAULT_SHEET_NAME not in candidate_sheets:
            candidate_sheets.append(self.DEFAULT_SHEET_NAME)

        for s in sheet_names:
            if s not in candidate_sheets:
                candidate_sheets.append(s)

        for s in candidate_sheets:
            df = pd.read_excel(file_path, sheet_name=s, header=None, engine=engine)
            if self._looks_like_molinete_sheet(df):
                return df, s

        fallback = candidate_sheets[0]
        df = pd.read_excel(file_path, sheet_name=fallback, header=None, engine=engine)
        return df, fallback

    def _looks_like_molinete_sheet(self, df: pd.DataFrame) -> bool:
        has_aforo = self._find_label(df, "AFORO") is not None
        has_vert = self._find_label(df, "Vert") is not None
        has_totales = self._find_label(df, "TOTALES") is not None
        return has_aforo or (has_vert and has_totales)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    def _parse_summary(
        self,
        df: pd.DataFrame,
        file_path: str,
        station_id: str,
        measurement_date: dt.date,
        measurement_time: dt.time,
        start_time: Optional[dt.time],
        end_time: Optional[dt.time],
        raw_source_file: str,
        raw_sheet_name: str,
        points_df: pd.DataFrame,
    ) -> pd.DataFrame:

        estacion_num = self._value_right_of_label(df, "ESTACION")
        nombre = self._value_right_of_label(df, "NOMBRE")
        curso = self._value_right_of_label(df, "CURSO")

        esc_ini = self._to_float(self._value_right_of_label(df, "Esc. Ini"))
        esc_fin = self._to_float(self._value_right_of_label(df, "Esc. Fin"))

        molinete = self._value_near_label(
            df,
            "Molinete",
            preferred_offsets=[(0, 1), (0, 2), (1, 0), (1, 1)],
        )

        helice = self._value_for_helice(df)

        realizado = self._value_right_of_label(df, "Realizado")
        calculado = self._value_right_of_label(df, "Calculado")

        tipo_metodo = self._value_right_of_label(df, "Tipo y Método")
        todos_los_casos = self._value_right_of_label(df, "Todos los casos")
        segunda_vuelta_desde = self._to_float(self._value_right_of_label(df, "2a. vuelta desde"))
        correccion_c = self._to_float(self._value_right_of_label(df, "Corrección C"))

        k_lim_values = self._numeric_values_right_of_label(df, "K(lim)", max_values=2)
        a_values = self._numeric_values_right_of_label(df, "A =", max_values=3)
        b_values = self._numeric_values_right_of_label(df, "B =", max_values=3)

        ubicacion_text = self._value_below_or_right_of_label(df, "UBICACIÓN DEL PERFIL")
        coord_y, coord_x = self._parse_coordinates(ubicacion_text)

        observaciones = self._value_for_observaciones(df)

        escala_media_m = self._to_float(self._value_right_of_label(df, "Escala media"))
        q_m3s = self._to_float(self._value_right_of_label(df, "Caudal"))
        area_m2 = self._to_float(self._value_right_of_label(df, "Área"))
        vel_media_ms = self._to_float(self._value_right_of_label(df, "Vel. Media"))
        prof_max_m = self._to_float(self._value_right_of_label(df, "Prof. máxima"))
        radio_hidraulico_m = self._to_float(self._value_right_of_label(df, "Radio Hidráulico"))
        k_star = self._to_float(self._value_right_of_label(df, "K*=v/R2/3"))

        totals = self._read_totals_row(df)
        if totals:
            area_tot, vel_media_tot, q_tot = totals

            # Los totales de la fila TOTALES son la fuente más confiable.
            area_m2 = area_tot
            vel_media_ms = vel_media_tot
            q_m3s = q_tot

        margin = self._parse_profile_margin(df)
        rev_en_s = self._parse_rev_en(df)

        prof_media_m = None
        ancho_m = None

        if not points_df.empty:
            prof_media_m = points_df["prof_m"].dropna().mean()

            progr_values = points_df["progr_m"].dropna().sort_values().tolist()
            if len(progr_values) >= 2:
                max_progr = progr_values[-1]
                prev_progr = progr_values[-2]
                ancho_m = max_progr + 0.5 * (max_progr - prev_progr)
            elif len(progr_values) == 1:
                ancho_m = progr_values[0]

        summary_payload = {
            "source_file_path": file_path,
            "estacion_num": self._clean_scalar(estacion_num),
            "nombre": self._clean_scalar(nombre),
            "curso": self._clean_scalar(curso),
            "fecha": measurement_date.strftime("%Y-%m-%d"),
            "hora_ini": start_time.strftime("%H:%M:%S") if start_time else None,
            "hora_fin": end_time.strftime("%H:%M:%S") if end_time else None,
            "esc_ini_m": esc_ini,
            "esc_fin_m": esc_fin,
            "molinete": self._clean_scalar(molinete),
            "helice": self._clean_scalar(helice),
            "realizado": self._clean_scalar(realizado),
            "calculado": self._clean_scalar(calculado),
            "tipo_metodo_aforo": self._clean_scalar(tipo_metodo),
            "todos_los_casos": self._clean_scalar(todos_los_casos),
            "segunda_vuelta_desde_m": segunda_vuelta_desde,
            "correccion_c": correccion_c,
            "k_lim_1": k_lim_values[0] if len(k_lim_values) > 0 else None,
            "k_lim_2": k_lim_values[1] if len(k_lim_values) > 1 else None,
            "a_1": a_values[0] if len(a_values) > 0 else None,
            "a_2": a_values[1] if len(a_values) > 1 else None,
            "a_3": a_values[2] if len(a_values) > 2 else None,
            "b_1": b_values[0] if len(b_values) > 0 else None,
            "b_2": b_values[1] if len(b_values) > 1 else None,
            "b_3": b_values[2] if len(b_values) > 2 else None,
            "ubicacion_perfil": self._clean_scalar(ubicacion_text),
            "coord_y": coord_y,
            "coord_x": coord_x,
            "observaciones": self._clean_scalar(observaciones),
            "escala_media_m": escala_media_m,
            "q_m3s": q_m3s,
            "area_m2": area_m2,
            "vel_media_ms": vel_media_ms,
            "prof_max_m": prof_max_m,
            "radio_hidraulico_m": radio_hidraulico_m,
            "k_star": k_star,
            "profile_start_margin": margin,
            "rev_en_s": rev_en_s,
            "prof_media_m": prof_media_m,
            "ancho_m": ancho_m,
            "n_points": int(len(points_df)),
        }

        return pd.DataFrame([{
            "station_id": station_id,
            "measurement_date": measurement_date.strftime("%Y-%m-%d"),
            "measurement_time": measurement_time.strftime("%H:%M:%S"),
            "raw_source_file": raw_source_file,
            "raw_sheet_name": raw_sheet_name,

            "estacion_num": self._clean_scalar(estacion_num),
            "nombre": self._clean_scalar(nombre),
            "curso": self._clean_scalar(curso),
            "start_time": start_time.strftime("%H:%M:%S") if start_time else None,
            "end_time": end_time.strftime("%H:%M:%S") if end_time else None,
            "esc_ini_m": esc_ini,
            "esc_fin_m": esc_fin,
            "molinete": self._clean_scalar(molinete),
            "helice": self._clean_scalar(helice),
            "realizado": self._clean_scalar(realizado),
            "calculado": self._clean_scalar(calculado),
            "tipo_metodo_aforo": self._clean_scalar(tipo_metodo),
            "todos_los_casos": self._clean_scalar(todos_los_casos),
            "segunda_vuelta_desde_m": segunda_vuelta_desde,
            "correccion_c": correccion_c,

            "k_lim_1": k_lim_values[0] if len(k_lim_values) > 0 else None,
            "k_lim_2": k_lim_values[1] if len(k_lim_values) > 1 else None,
            "a_1": a_values[0] if len(a_values) > 0 else None,
            "a_2": a_values[1] if len(a_values) > 1 else None,
            "a_3": a_values[2] if len(a_values) > 2 else None,
            "b_1": b_values[0] if len(b_values) > 0 else None,
            "b_2": b_values[1] if len(b_values) > 1 else None,
            "b_3": b_values[2] if len(b_values) > 2 else None,

            "ubicacion_perfil": self._clean_scalar(ubicacion_text),
            "coord_y": coord_y,
            "coord_x": coord_x,
            "observaciones": self._clean_scalar(observaciones),

            "escala_media_m": escala_media_m,
            "q_m3s": q_m3s,
            "area_m2": area_m2,
            "vel_media_ms": vel_media_ms,
            "prof_max_m": prof_max_m,
            "radio_hidraulico_m": radio_hidraulico_m,
            "k_star": k_star,

            "profile_start_margin": margin,
            "rev_en_s": rev_en_s,

            "prof_media_m": prof_media_m,
            "ancho_m": ancho_m,
            "n_points": int(len(points_df)),

            "extras_json": json.dumps(summary_payload, ensure_ascii=False),
        }])

    # ------------------------------------------------------------------
    # Points
    # ------------------------------------------------------------------
    def _parse_points(
        self,
        df: pd.DataFrame,
        station_id: str,
        measurement_date: str,
        measurement_time: str,
        raw_source_file: str,
        raw_sheet_name: str,
    ) -> pd.DataFrame:

        header_pos = self._find_points_header(df)
        if header_pos is None:
            raise MolineteExcelFormatMismatch("Could not find Points header row.")

        header_row, _ = header_pos
        start_row = header_row + self.POINTS_START_OFFSET

        totals_pos = self._find_label(df, "TOTALES")
        end_row = totals_pos[0] if totals_pos else len(df)

        rows: List[Dict[str, Any]] = []
        point_index = 1

        r = start_row

        while r < end_row:
            vert_raw = self._cell(df, r, 0)
            progr = self._to_float(self._cell(df, r, 2))

            if progr is None:
                r += 1
                continue

            prof = self._to_float(self._cell(df, r, 3))
            angle = self._to_float(self._cell(df, r, 4))
            n_points = self._to_int(self._cell(df, r, 6))

            rev_values = self._collect_vertical_values(
                df, r, 5, end_row, max_values=self.MAX_REV_VALUES
            )
            vel_point_values = self._collect_vertical_values(
                df, r, 7, end_row, max_values=self.MAX_VEL_POINT_VALUES
            )

            vel_media_vert_ms = self._to_float(self._cell(df, r, 9))
            vel_media_secc_ms = self._to_float(self._cell(df, r, 10))
            area_m2 = self._to_float(self._cell(df, r, 11))
            q_m3s = self._to_float(self._cell(df, r, 12))
            #q_percent = self._to_float(self._cell(df, r, 13))
            q_percent_raw = self._to_float(self._cell(df, r + 2, 13))
            q_percent = q_percent_raw * 100 if q_percent_raw is not None else None

            vert_label = self._clean_vert_label(vert_raw)

            payload = {
                "vert_label": vert_label,
                "progr_m": progr,
                "prof_m": prof,
                "angle_hor_deg": angle,
                "n_points": n_points,
                "rev_values": rev_values,
                "vel_point_values": vel_point_values,
                "vel_media_vert_ms": vel_media_vert_ms,
                "vel_media_secc_ms": vel_media_secc_ms,
                "area_m2": area_m2,
                "q_m3s": q_m3s,
                "q_percent": q_percent,
            }

            rows.append({
                "station_id": station_id,
                "measurement_date": measurement_date,
                "measurement_time": measurement_time,
                "raw_source_file": raw_source_file,
                "raw_sheet_name": raw_sheet_name,
                "point_index": point_index,

                "vert_label": vert_label,
                "progr_m": progr,
                "prof_m": prof,
                "angle_hor_deg": angle,
                "n_points": n_points,

                "rev_1_s": rev_values[0] if len(rev_values) > 0 else None,
                "rev_2_s": rev_values[1] if len(rev_values) > 1 else None,
                "rev_3_s": rev_values[2] if len(rev_values) > 2 else None,

                "vel_point_1_ms": vel_point_values[0] if len(vel_point_values) > 0 else None,
                "vel_point_2_ms": vel_point_values[1] if len(vel_point_values) > 1 else None,
                "vel_point_3_ms": vel_point_values[2] if len(vel_point_values) > 2 else None,

                "vel_media_vert_ms": vel_media_vert_ms,
                "vel_media_secc_ms": vel_media_secc_ms,
                "area_m2": area_m2,
                "q_m3s": q_m3s,
                "q_percent": q_percent,

                "extras_json": json.dumps(payload, ensure_ascii=False),
            })

            point_index += 1
            r += 1

        if not rows:
            raise MolineteExcelFormatMismatch("No valid Points rows found.")

        return pd.DataFrame(rows)

    def _collect_vertical_values(
        self,
        df: pd.DataFrame,
        start_row: int,
        col: int,
        end_row: int,
        max_values: int,
    ) -> List[float]:
        values: List[float] = []

        for rr in range(start_row, min(start_row + max_values, end_row)):
            value = self._to_float(self._cell(df, rr, col))
            if value is not None:
                values.append(value)

        return values

    def _find_points_header(self, df: pd.DataFrame) -> Optional[Tuple[int, int]]:
        for r in range(len(df)):
            for c in range(df.shape[1]):
                text = self._norm_text(self._cell(df, r, c))
                if "vert" in text and ("n" in text or "no" in text):
                    return r, c
        return None

    # ------------------------------------------------------------------
    # Summary helpers
    # ------------------------------------------------------------------
    def _read_totals_row(self, df: pd.DataFrame) -> Optional[Tuple[Optional[float], Optional[float], Optional[float]]]:
        """
        En la fila TOTALES:
        K = Vel. Media
        L = Área
        M = Caudal
        """
        pos = self._find_label(df, "TOTALES")
        if pos is None:
            return None

        r, _ = pos

        vel_media_ms = self._to_float(self._cell(df, r, 10))  # K
        area_m2 = self._to_float(self._cell(df, r, 11))        # L
        q_m3s = self._to_float(self._cell(df, r, 12))          # M

        return area_m2, vel_media_ms, q_m3s

    def _value_for_helice(self, df: pd.DataFrame) -> Any:
        """
        Busca el valor de Hélice evitando capturar la tabla de calibración
        donde aparecen K(lim), A y B.
        """
        pos = self._find_label_exactish(df, "Hélice")
        if pos is None:
            return None

        r, c = pos

        candidates = [
            self._cell(df, r, c + 1),
            self._cell(df, r, c + 2),
            self._cell(df, r, c + 3),
            self._cell(df, r + 1, c + 1),
            self._cell(df, r + 1, c + 2),
            self._cell(df, r + 2, c + 1),
            self._cell(df, r + 2, c + 2),
        ]

        forbidden = ["k(lim", "k lim", "a =", "b =", "todos los casos"]

        for value in candidates:
            if not self._is_meaningful(value):
                continue

            text = str(value).strip()
            norm = self._norm_text(text)

            if any(x in norm for x in forbidden):
                continue

            return text

        return None

    def _value_for_observaciones(self, df: pd.DataFrame) -> Optional[str]:
        pos = self._find_label_exactish(df, "Observaciones")
        if pos is None:
            return None

        r, c = pos
        parts: List[str] = []

        stop_words = [
            "escala media",
            "caudal",
            "area",
            "vel media",
            "prof maxima",
            "radio hidraulico",
            "k*=v",
            "datos",
            "velocidades",
            "vert",
            "progr",
            "totales",
        ]

        for rr in range(r, min(r + 8, len(df))):
            start_col = c + 1 if rr == r else c

            for cc in range(start_col, min(c + 14, df.shape[1])):
                value = self._cell(df, rr, cc)

                if not self._is_meaningful(value):
                    continue

                text = str(value).strip()
                norm = self._norm_text(text)

                if any(word in norm for word in stop_words):
                    return " ".join(parts).strip() if parts else None

                # Saltar números, códigos y valores de calibración.
                if not re.search(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]", text):
                    continue

                if re.fullmatch(r"\d+[-–]\d+", text):
                    continue

                if any(x in norm for x in ["k(lim", "a =", "b =", "todos los casos"]):
                    continue

                parts.append(text)

        return " ".join(parts).strip() if parts else None

    def _parse_profile_margin(self, df: pd.DataFrame) -> Optional[str]:
        for r in range(len(df)):
            for c in range(df.shape[1]):
                text = self._norm_text(self._cell(df, r, c))

                if "perfil inicia" in text:
                    if "m.i" in text or "mi" in text:
                        return "MI"
                    if "m.d" in text or "md" in text:
                        return "MD"

        for r in range(len(df) - 2):
            row_texts = [self._norm_text(self._cell(df, r, c)) for c in range(df.shape[1])]

            if "m.i" in row_texts and "m.d" in row_texts:
                mi_col = row_texts.index("m.i")
                md_col = row_texts.index("m.d")

                for rr in range(r + 1, min(r + 4, len(df))):
                    mi_val = self._norm_text(self._cell(df, rr, mi_col))
                    md_val = self._norm_text(self._cell(df, rr, md_col))

                    if "x" in mi_val:
                        return "MI"
                    if "x" in md_val:
                        return "MD"

        return None

    def _parse_rev_en(self, df: pd.DataFrame) -> Optional[float]:
        pos = self._find_label(df, "Rev")
        if pos is None:
            return None

        r, c = pos

        candidates = [
            self._cell(df, r, c + 1),
            self._cell(df, r + 1, c),
            self._cell(df, r + 1, c + 1),
        ]

        for value in candidates:
            f = self._to_float(value)
            if f is not None:
                return f

        return None

    def _parse_coordinates(self, text: Any) -> Tuple[Optional[float], Optional[float]]:
        if text is None or pd.isna(text):
            return None, None

        s = str(text).replace(",", ".")

        y = None
        x = None

        my = re.search(r"Y\s*=\s*(-?\d+(?:\.\d+)?)", s, flags=re.IGNORECASE)
        mx = re.search(r"X\s*=\s*(-?\d+(?:\.\d+)?)", s, flags=re.IGNORECASE)

        if my:
            y = self._to_float(my.group(1))
        if mx:
            x = self._to_float(mx.group(1))

        return y, x

    # ------------------------------------------------------------------
    # Label search
    # ------------------------------------------------------------------
    def _find_label(self, df: pd.DataFrame, label: str) -> Optional[Tuple[int, int]]:
        target = self._norm_text(label)

        for r in range(len(df)):
            for c in range(df.shape[1]):
                text = self._norm_text(self._cell(df, r, c))
                if target in text:
                    return r, c

        return None

    def _find_label_exactish(self, df: pd.DataFrame, label: str) -> Optional[Tuple[int, int]]:
        target = self._norm_text(label)

        for r in range(len(df)):
            for c in range(df.shape[1]):
                text = self._norm_text(self._cell(df, r, c))

                if text == target:
                    return r, c

                if text.startswith(target):
                    return r, c

        return None

    def _value_right_of_label(self, df: pd.DataFrame, label: str, max_scan: int = 8) -> Any:
        pos = self._find_label(df, label)
        if pos is None:
            return None

        r, c = pos

        for cc in range(c + 1, min(c + 1 + max_scan, df.shape[1])):
            value = self._cell(df, r, cc)
            if self._is_meaningful(value):
                return value

        return None

    def _value_near_label(
        self,
        df: pd.DataFrame,
        label: str,
        preferred_offsets: List[Tuple[int, int]],
    ) -> Any:
        pos = self._find_label(df, label)
        if pos is None:
            return None

        r, c = pos

        for dr, dc in preferred_offsets:
            value = self._cell(df, r + dr, c + dc)
            if self._is_meaningful(value):
                return value

        return None

    def _value_below_or_right_of_label(self, df: pd.DataFrame, label: str) -> Any:
        pos = self._find_label(df, label)
        if pos is None:
            return None

        r, c = pos

        right = self._value_right_of_label(df, label, max_scan=6)
        if self._is_meaningful(right):
            return right

        for rr in range(r + 1, min(r + 5, len(df))):
            value = self._cell(df, rr, c)
            if self._is_meaningful(value):
                return value

        return None

    def _numeric_values_right_of_label(self, df: pd.DataFrame, label: str, max_values: int = 3) -> List[float]:
        pos = self._find_label(df, label)
        if pos is None:
            return []

        r, c = pos
        values: List[float] = []

        for cc in range(c + 1, df.shape[1]):
            value = self._to_float(self._cell(df, r, cc))
            if value is not None:
                values.append(value)
                if len(values) >= max_values:
                    break

        return values

    # ------------------------------------------------------------------
    # Low-level helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _cell(df: pd.DataFrame, r: int, c: int) -> Any:
        if r < 0 or r >= len(df):
            return None
        if c < 0 or c >= df.shape[1]:
            return None

        value = df.iat[r, c]

        if pd.isna(value):
            return None

        return value

    @staticmethod
    def _is_meaningful(value: Any) -> bool:
        if value is None:
            return False
        if pd.isna(value):
            return False
        if isinstance(value, str) and value.strip() == "":
            return False
        return True

    @staticmethod
    def _norm_text(value: Any) -> str:
        if value is None:
            return ""

        if pd.isna(value):
            return ""

        s = str(value).strip().lower()

        replacements = {
            "á": "a",
            "é": "e",
            "í": "i",
            "ó": "o",
            "ú": "u",
            "ü": "u",
            "ñ": "n",
            "º": "o",
            "°": "o",
            ":": "",
        }

        for a, b in replacements.items():
            s = s.replace(a, b)

        s = re.sub(r"\s+", " ", s)
        return s

    @staticmethod
    def _clean_scalar(value: Any) -> Optional[Any]:
        if value is None:
            return None

        if pd.isna(value):
            return None

        if isinstance(value, str):
            value = value.strip()
            return value if value != "" else None

        return value

    @staticmethod
    def _clean_station_id(value: Any) -> Optional[str]:
        if value is None or pd.isna(value):
            return None

        s = str(value).strip()

        m = re.search(r"\bP\s*([0-9]{1,4})\b", s, flags=re.IGNORECASE)
        if m:
            return f"P{int(m.group(1))}"

        return None

    @staticmethod
    def _clean_vert_label(value: Any) -> Optional[str]:
        if value is None or pd.isna(value):
            return None

        if isinstance(value, float) and abs(value - round(value)) < 1e-9:
            return str(int(round(value)))

        return str(value).strip()

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        if value is None:
            return None

        if pd.isna(value):
            return None

        if isinstance(value, (int, float)):
            return float(value)

        s = str(value).strip()

        if s == "" or s == "-":
            return None

        s = s.replace(",", ".")

        try:
            return float(s)
        except Exception:
            return None

    @staticmethod
    def _to_int(value: Any) -> Optional[int]:
        f = MolineteExcelAdapter._to_float(value)
        if f is None:
            return None

        return int(round(f))

    @staticmethod
    def _to_date(value: Any) -> Optional[dt.date]:
        if value is None:
            return None

        if pd.isna(value):
            return None

        if isinstance(value, dt.datetime):
            return value.date()

        if isinstance(value, dt.date):
            return value

        if isinstance(value, (int, float)) and float(value) > 1000:
            try:
                base = dt.datetime(1899, 12, 30)
                return (base + dt.timedelta(days=float(value))).date()
            except Exception:
                return None

        s = str(value).strip()

        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return dt.datetime.strptime(s, fmt).date()
            except Exception:
                pass

        return None

    @staticmethod
    def _to_time(value: Any) -> Optional[dt.time]:
        if value is None:
            return None

        if pd.isna(value):
            return None

        if isinstance(value, dt.datetime):
            return value.time().replace(microsecond=0)

        if isinstance(value, dt.time):
            return value.replace(microsecond=0)

        if isinstance(value, (int, float)):
            total_seconds = int(round(float(value) * 24 * 3600))
            total_seconds = max(0, min(total_seconds, 24 * 3600 - 1))

            hh = total_seconds // 3600
            mm = (total_seconds % 3600) // 60
            ss = total_seconds % 60

            return dt.time(hh, mm, ss)

        s = str(value).strip()

        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return dt.datetime.strptime(s, fmt).time().replace(microsecond=0)
            except Exception:
                pass

        return None

    @staticmethod
    def _infer_station_id(file_path: str) -> str:
        base = os.path.basename(file_path)

        m = re.search(r"\bP(\d{1,4})\b", base, flags=re.IGNORECASE)
        if m:
            return f"P{int(m.group(1))}"

        m = re.search(r"[\\/](P\d{1,4})[\\/]", file_path, flags=re.IGNORECASE)
        if m:
            return m.group(1).upper()

        return "PUNK"

    @staticmethod
    def _infer_date_from_path_or_filename(file_path: str) -> Optional[dt.date]:
        matches = re.findall(r"(20\d{2})(\d{2})(\d{2})", file_path)

        for y, mo, d in matches:
            try:
                return dt.date(int(y), int(mo), int(d))
            except Exception:
                continue

        matches = re.findall(r"\b(\d{2})(\d{2})(20\d{2})\b", file_path)

        for d, mo, y in matches:
            try:
                return dt.date(int(y), int(mo), int(d))
            except Exception:
                continue

        return None