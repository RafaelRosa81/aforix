from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aforix.export.sih.config import (
    get_lookup_file_paths,
    get_normalized_input_dir,
    get_output_dir,
    get_raw_canonical_input_dir,
    load_sih_config,
)
from aforix.export.sih.inputs import (
    load_normalized_summary,
    load_raw_canonical_summary,
    load_selection_file,
    resolve_measurement,
    resolve_optional_measurement,
)
from aforix.export.sih.mappings import (
    build_measurement_datetime,
    build_sdh_actuaciones_row,
    build_sdh_aforos_row,
    get_instrument_config,
    load_lookup_tables,
    resolve_instrument_lookup_id,
    resolve_instrumentos_rangos_lookup_id,
    resolve_station_lookup_id,
    resolve_tipo_aforo_lookup_id,
)
from aforix.export.sih.schema import (
    SDH_ACTUACIONES_COLUMNS,
    SDH_AFOROS_COLUMNS,
)
from aforix.export.sih.writers import write_csv


@dataclass(frozen=True)
class SihExportRequest:
    sih_config_path: Path
    selection_file: Path
    interactive: bool = False


@dataclass(frozen=True)
class SihExportResult:
    output_dir: Path
    exported_files: tuple[Path, ...]



def run_sih_export(request: SihExportRequest) -> SihExportResult:
    sih_config = load_sih_config(request.sih_config_path)

    selection_df = load_selection_file(request.selection_file)

    normalized_root = get_normalized_input_dir(sih_config)
    raw_canonical_root = get_raw_canonical_input_dir(sih_config)
    output_dir = get_output_dir(sih_config)

    lookup_paths = get_lookup_file_paths(sih_config)
    lookup_tables = load_lookup_tables(lookup_paths)

    datetime_format = (
        sih_config["sih"]
        .get("datetime", {})
        .get("output_format", "%d/%m/%Y %H:%M:%S")
    )

    output_cfg = sih_config["sih"].get("output", {})
    output_names = output_cfg.get("output_names", {})
    delimiter = output_cfg.get("delimiter", ",")
    encoding = output_cfg.get("encoding", "utf-8-sig")

    exported_files: list[Path] = []

    for _, row in selection_df.iterrows():
        instrument = str(row["instrument"])

        instrument_cfg = get_instrument_config(sih_config, instrument)

        summary_df = load_normalized_summary(normalized_root, instrument)
        raw_summary_df = load_raw_canonical_summary(raw_canonical_root, instrument)

        measurement = resolve_measurement(summary_df, row)
        raw_measurement = resolve_optional_measurement(raw_summary_df, row)

        dt = build_measurement_datetime(measurement)

        id_estacion = resolve_station_lookup_id(
            measurement,
            sih_config,
            lookup_tables,
        )

        id_instrumento = resolve_instrument_lookup_id(
            instrument_cfg,
            sih_config,
            lookup_tables,
        )

        id_tipo_aforo = resolve_tipo_aforo_lookup_id(
            instrument_cfg,
            sih_config,
            lookup_tables,
        )

        id_instrumentos_rangos = resolve_instrumentos_rangos_lookup_id(
            instrument_cfg,
            sih_config,
            lookup_tables,
        )

        actuaciones_row = build_sdh_actuaciones_row(
            measurement,
            instrument_cfg,
            dt,
            datetime_format,
            id_estacion=id_estacion,
            id_instrumento=id_instrumento,
            raw_measurement=raw_measurement,
        )

        aforos_row = build_sdh_aforos_row(
            measurement,
            instrument_cfg,
            dt,
            datetime_format,
            id_estacion=id_estacion,
            id_instrumento=id_instrumento,
            id_tipo_aforo=id_tipo_aforo,
            id_instrumentos_rangos=id_instrumentos_rangos,
            raw_measurement=raw_measurement,
        )

        station_id = str(measurement.get("station_id", "unknown"))
        ymd = dt.strftime("%Y%m%d")
        hms = dt.strftime("%H%M%S")
        export_id = str(row.get("export_id", "EXPORT"))

        actuaciones_name = output_names.get(
            "actuaciones",
            "ID_{export_id}_actuacion_{station_id}_{YYYYMMDD}_{HHMMSS}.csv",
        ).format(
            export_id=export_id,
            station_id=station_id,
            YYYYMMDD=ymd,
            HHMMSS=hms,
        )

        aforos_name = output_names.get(
            "aforos",
            "ID_{export_id}_aforo_{station_id}_{YYYYMMDD}_{HHMMSS}.csv",
        ).format(
            export_id=export_id,
            station_id=station_id,
            YYYYMMDD=ymd,
            HHMMSS=hms,
        )

        actuaciones_path = write_csv(
            actuaciones_row,
            SDH_ACTUACIONES_COLUMNS,
            output_dir / actuaciones_name,
            delimiter=delimiter,
            encoding=encoding,
        )

        aforos_path = write_csv(
            aforos_row,
            SDH_AFOROS_COLUMNS,
            output_dir / aforos_name,
            delimiter=delimiter,
            encoding=encoding,
        )

        exported_files.extend([actuaciones_path, aforos_path])

    return SihExportResult(
        output_dir=output_dir,
        exported_files=tuple(exported_files),
    )
