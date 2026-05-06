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


def load_lookup_tables(lookup_paths: dict[str, Any]) -> dict[str, pd.DataFrame]:
    return {
        name: pd.read_csv(path, dtype=str).fillna("")
        for name, path in lookup_paths.items()
    }


def resolve_station_lookup_id(
    measurement: pd.Series,
    sih_config: dict[str, Any],
    lookup_tables: dict[str, pd.DataFrame],
) -> str:
    station_lookup = sih_config["sih"]["station_mapping"]["lookup"]

    table_name = station_lookup["file"]
    key_column = station_lookup["key_column"]
    value_column = station_lookup["value_column"]

    lookup_df = lookup_tables[table_name]

    lookup_key = station_id_to_lookup_key(measurement.get("station_id", ""))

    matches = lookup_df[lookup_df[key_column].astype(str) == lookup_key]

    if matches.empty:
        raise ValueError(
            f"Station lookup failed for station_id={measurement.get('station_id')} -> key={lookup_key}"
        )

    return str(matches.iloc[0][value_column])


def resolve_instrument_lookup_id(
    instrument_cfg: dict[str, Any],
    sih_config: dict[str, Any],
    lookup_tables: dict[str, pd.DataFrame],
) -> str:
    lookup_cfg = sih_config["sih"]["lookup_tables"]["instrumentos"]

    table_name = lookup_cfg["file"]
    key_column = lookup_cfg["key_column"]
    value_column = lookup_cfg["value_column"]

    lookup_df = lookup_tables[table_name]

    instrument_code = instrument_cfg.get("aforix_code", "")

    matches = lookup_df[lookup_df[key_column].astype(str) == instrument_code]

    if matches.empty:
        raise ValueError(
            f"Instrument lookup failed for instrument code={instrument_code}"
        )

    return str(matches.iloc[0][value_column])


def build_sdh_actuaciones_row(
    measurement: pd.Series,
    instrument_cfg: dict[str, Any],
    dt: datetime,
    datetime_format: str,
    *,
    id_estacion: str,
    id_instrumento: str,
) -> dict[str, Any]:
    return {
        "id": "",
        "id_estacion": id_estacion,
        "id_operador": "",
        "id_tipo_actuacion": instrument_cfg.get("id_tipo_actuacion", ""),
        "id_instrumento": id_instrumento,
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
    *,
    id_estacion: str,
    id_instrumento: str,
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
        "id_estacion": id_estacion,
        "id_instrumento": id_instrumento,
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
