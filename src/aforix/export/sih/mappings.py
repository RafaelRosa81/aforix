from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from aforix.export.sih.io import read_csv_robust



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
        name: read_csv_robust(path, dtype=str, fillna_value="")
        for name, path in lookup_paths.items()
    }



def _lookup_value(
    lookup_tables: dict[str, pd.DataFrame],
    *,
    table_name: str,
    key_column: str,
    value_column: str,
    key: str,
    label: str,
    required: bool = True,
) -> str:
    if key in (None, ""):
        if required:
            raise ValueError(f"Missing lookup key for {label}")
        return ""

    lookup_df = lookup_tables[table_name]
    matches = lookup_df[lookup_df[key_column].astype(str) == str(key)]

    if matches.empty:
        if required:
            raise ValueError(f"Lookup failed for {label}: key={key}")
        return ""

    return str(matches.iloc[0][value_column])



def resolve_station_lookup_id(
    measurement: pd.Series,
    sih_config: dict[str, Any],
    lookup_tables: dict[str, pd.DataFrame],
) -> str:
    station_lookup = sih_config["sih"]["station_mapping"]["lookup"]
    lookup_key = station_id_to_lookup_key(measurement.get("station_id", ""))

    return _lookup_value(
        lookup_tables,
        table_name=station_lookup["file"],
        key_column=station_lookup["key_column"],
        value_column=station_lookup["value_column"],
        key=lookup_key,
        label=f"station_id={measurement.get('station_id')} -> {lookup_key}",
        required=True,
    )



def resolve_instrument_lookup_id(
    instrument_cfg: dict[str, Any],
    sih_config: dict[str, Any],
    lookup_tables: dict[str, pd.DataFrame],
) -> str:
    lookup_cfg = sih_config["sih"]["lookup_tables"]["instrumentos"]
    instrument_code = instrument_cfg.get("aforix_code", "")

    return _lookup_value(
        lookup_tables,
        table_name=lookup_cfg["file"],
        key_column=lookup_cfg["key_column"],
        value_column=lookup_cfg["value_column"],
        key=instrument_code,
        label=f"instrument code={instrument_code}",
        required=True,
    )



def resolve_tipo_aforo_lookup_id(
    instrument_cfg: dict[str, Any],
    sih_config: dict[str, Any],
    lookup_tables: dict[str, pd.DataFrame],
) -> str:
    direct_value = instrument_cfg.get("id_tipo_aforo")
    if direct_value not in (None, ""):
        return str(direct_value)

    lookup_key = instrument_cfg.get("tipo_aforo_lookup")
    lookup_cfg = sih_config["sih"]["lookup_tables"]["tipos_aforos"]

    return _lookup_value(
        lookup_tables,
        table_name=lookup_cfg["file"],
        key_column=lookup_cfg["key_column"],
        value_column=lookup_cfg["value_column"],
        key=lookup_key,
        label=f"tipo_aforo={lookup_key}",
        required=False,
    )



def resolve_instrumentos_rangos_lookup_id(
    instrument_cfg: dict[str, Any],
    sih_config: dict[str, Any],
    lookup_tables: dict[str, pd.DataFrame],
) -> str:
    direct_value = instrument_cfg.get("id_instrumentos_rangos")
    if direct_value not in (None, ""):
        return str(direct_value)

    lookup_key = instrument_cfg.get("instrumentos_rangos_lookup")
    lookup_cfg = sih_config["sih"]["lookup_tables"]["instrumentos_rangos"]

    return _lookup_value(
        lookup_tables,
        table_name=lookup_cfg["file"],
        key_column=lookup_cfg["key_column"],
        value_column=lookup_cfg["value_column"],
        key=lookup_key,
        label=f"instrumentos_rangos={lookup_key}",
        required=False,
    )



def _raw_field(raw_measurement: pd.Series | None, instrument_cfg: dict[str, Any], key: str) -> str:
    if raw_measurement is None:
        return ""

    raw_fields = instrument_cfg.get("raw_canonical_fields", {})
    column = raw_fields.get(key)

    if column in (None, ""):
        return ""

    return str(raw_measurement.get(column, ""))



def build_sdh_actuaciones_row(
    measurement: pd.Series,
    instrument_cfg: dict[str, Any],
    dt: datetime,
    datetime_format: str,
    *,
    id_estacion: str,
    id_instrumento: str,
    raw_measurement: pd.Series | None = None,
) -> dict[str, Any]:
    return {
        "id": "",
        "id_estacion": id_estacion,
        "id_operador": _raw_field(raw_measurement, instrument_cfg, "id_operador"),
        "id_tipo_actuacion": instrument_cfg.get("id_tipo_actuacion", ""),
        "id_instrumento": id_instrumento,
        "fecha": format_datetime(dt, datetime_format),
        "pendiente": False,
        "relevante": False,
        "lectura_escala": _raw_field(raw_measurement, instrument_cfg, "lectura_escala"),
        "observaciones": _raw_field(raw_measurement, instrument_cfg, "observaciones"),
    }



def build_sdh_aforos_row(
    measurement: pd.Series,
    instrument_cfg: dict[str, Any],
    dt: datetime,
    datetime_format: str,
    *,
    id_estacion: str,
    id_instrumento: str,
    id_tipo_aforo: str,
    id_instrumentos_rangos: str,
    raw_measurement: pd.Series | None = None,
) -> dict[str, Any]:
    normalized_fields = instrument_cfg.get("normalized_fields", {})

    def field(name: str) -> str:
        column = normalized_fields.get(name)
        if not column:
            return ""
        return measurement.get(column, "")

    escala_inicio = _raw_field(raw_measurement, instrument_cfg, "escala_inicio")
    escala_fin = _raw_field(raw_measurement, instrument_cfg, "escala_fin")
    escala_media = _raw_field(raw_measurement, instrument_cfg, "escala_media")

    return {
        "ancho": field("ancho"),
        "caudal": field("caudal"),
        "escala_fin": escala_fin,
        "escala_inicio": escala_inicio,
        "escala_media": escala_media,
        "fecha_fin": format_datetime(dt, datetime_format),
        "fecha_inicio": format_datetime(dt, datetime_format),
        "id": "",
        "id_actuacion": "",
        "id_estacion": id_estacion,
        "id_instrumento": id_instrumento,
        "id_instrumentos_rangos": id_instrumentos_rangos,
        "id_perfil": "",
        "id_tipo_aforo": id_tipo_aforo,
        "observaciones": _raw_field(raw_measurement, instrument_cfg, "observaciones"),
        "profundidad": field("profundidad"),
        "seccion": field("seccion"),
        "velocidad_media": field("velocidad_media"),
        "radio_hidraulico": _raw_field(raw_measurement, instrument_cfg, "radio_hidraulico"),
        "nivel_confiabilidad": "",
    }
