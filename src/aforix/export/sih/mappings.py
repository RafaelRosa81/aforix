from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd


def station_id_to_lookup_key(station_id: str) -> str:
    cleaned = str(station_id).strip()

    if cleaned.upper().startswith("P"):
        cleaned = cleaned[1:]

    try:
        value = float(cleaned)
        return f"{value:.1f}"
    except ValueError:
        return cleaned


def build_measurement_datetime(measurement: pd.Series) -> datetime:
    date_str = str(measurement.get("measurement_date", "")).strip()
    time_str = str(measurement.get("measurement_time", "")).strip()

    date_str = date_str.replace("-", "")
    time_str = time_str.replace(":", "")[:6]

    return datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")


def format_datetime(dt: datetime, fmt: str) -> str:
    return dt.strftime(fmt)


def get_instrument_config(sih_config: dict[str, Any], instrument: str) -> dict[str, Any]:
    instruments = sih_config["sih"].get("instruments", {})

    if instrument not in instruments:
        raise KeyError(f"Instrument not configured in SIH config: {instrument}")

    return instruments[instrument]


def build_sdh_actuaciones_row(
    measurement: pd.Series,
    instrument_cfg: dict[str, Any],
    dt: datetime,
    datetime_format: str,
) -> dict[str, Any]:
    return {
        "id": "",
        "id_estacion": station_id_to_lookup_key(measurement.get("station_id", "")),
        "id_operador": "",
        "id_tipo_actuacion": instrument_cfg.get("id_tipo_actuacion", ""),
        "id_instrumento": instrument_cfg.get("id_instrumento", ""),
        "fecha": format_datetime(dt, datetime_format),
        "pendiente": False,
        "relevante": False,
        "lectura_escala": "",
        "observaciones": "",
    }


def build_sdh_aforos_row(
    measurement: pd.Series,
    instrument_cfg: dict[str, Any],
    dt: datetime,
    datetime_format: str,
) -> dict[str, Any]:
    normalized_fields = instrument_cfg.get("normalized_fields", {})

    def field(name: str) -> str:
        column = normalized_fields.get(name)
        if not column:
            return ""
        return measurement.get(column, "")

    return {
        "ancho": field("ancho"),
        "caudal": field("caudal"),
        "escala_fin": "",
        "escala_inicio": "",
        "escala_media": "",
        "fecha_fin": format_datetime(dt, datetime_format),
        "fecha_inicio": format_datetime(dt, datetime_format),
        "id": "",
        "id_actuacion": "",
        "id_estacion": station_id_to_lookup_key(measurement.get("station_id", "")),
        "id_instrumento": instrument_cfg.get("id_instrumento", ""),
        "id_instrumentos_rangos": instrument_cfg.get("id_instrumentos_rangos", ""),
        "id_perfil": "",
        "id_tipo_aforo": instrument_cfg.get("id_tipo_aforo", ""),
        "observaciones": "",
        "profundidad": field("profundidad"),
        "seccion": field("seccion"),
        "velocidad_media": field("velocidad_media"),
        "radio_hidraulico": "",
        "nivel_confiabilidad": "",
    }
