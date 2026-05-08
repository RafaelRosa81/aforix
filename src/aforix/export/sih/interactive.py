from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from aforix.export.sih.config import get_normalized_input_dir, get_output_dir
from aforix.export.sih.inputs import load_normalized_summary


REQUIRED_SUMMARY_COLUMNS = {"station_id", "measurement_date", "measurement_time"}


def _normalize_date(value: str) -> str:
    value = str(value).strip().replace("-", "").replace("/", "")
    if len(value) == 8 and value.isdigit():
        return value

    for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(str(value).strip(), fmt).strftime("%Y%m%d")
        except ValueError:
            continue

    return value


def _normalize_time(value: str) -> str:
    value = str(value).strip().replace(":", "").replace(".", "")
    if value.isdigit():
        return value.zfill(6)[-6:]
    return value


def _prompt_index_selection(
    title: str,
    options: list[str],
    *,
    allow_all: bool = True,
) -> list[str]:
    if not options:
        return []

    print(f"\n{title}")
    for idx, option in enumerate(options, start=1):
        print(f"[{idx}] {option}")

    if allow_all:
        print("[A] Todos")

    raw = input("Seleccione valores separados por coma: ").strip()

    if allow_all and raw.lower() in {"", "a", "all", "todos", "t"}:
        return options

    selected: list[str] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            selected.append(options[int(token) - 1])
        except (ValueError, IndexError):
            print(f"Valor ignorado: {token}")

    return selected


def _load_available_measurements(sih_config: dict[str, Any]) -> pd.DataFrame:
    normalized_root = get_normalized_input_dir(sih_config)
    instruments_cfg = sih_config["sih"].get("instruments", {})

    frames: list[pd.DataFrame] = []

    for instrument, cfg in instruments_cfg.items():
        if not cfg.get("enabled", True):
            continue

        try:
            summary = load_normalized_summary(normalized_root, instrument).copy()
        except FileNotFoundError:
            continue

        missing = REQUIRED_SUMMARY_COLUMNS - set(summary.columns)
        if missing:
            print(f"Instrumento omitido por columnas faltantes: {instrument} ({sorted(missing)})")
            continue

        summary["instrument"] = instrument
        summary["measurement_date"] = summary["measurement_date"].map(_normalize_date)
        summary["measurement_time"] = summary["measurement_time"].map(_normalize_time)
        frames.append(summary)

    if not frames:
        raise ValueError("No normalized Summary datasets were found for SIH interactive export.")

    return pd.concat(frames, ignore_index=True)


def _print_measurement_preview(df: pd.DataFrame) -> None:
    print("\nMediciones encontradas:")
    cols = ["station_id", "measurement_date", "measurement_time", "instrument"]
    optional = [c for c in ["q_total_m3s", "q_total_ls"] if c in df.columns]
    preview_cols = cols + optional

    for idx, row in df.reset_index(drop=True).iterrows():
        parts = [f"{col}={row.get(col, '')}" for col in preview_cols]
        print(f"[{idx + 1}] " + " | ".join(parts))


def build_interactive_selection(sih_config: dict[str, Any]) -> Path:
    print("\nAforix — SIH interactive export")
    print("================================")
    print(f"Normalized input: {get_normalized_input_dir(sih_config)}")
    print(f"Output directory: {get_output_dir(sih_config)}")

    measurements = _load_available_measurements(sih_config)

    instruments = sorted(measurements["instrument"].astype(str).unique().tolist())
    selected_instruments = _prompt_index_selection("Instrumentos disponibles", instruments)
    if not selected_instruments:
        raise ValueError("No instruments selected.")

    filtered = measurements[measurements["instrument"].astype(str).isin(selected_instruments)].copy()

    stations = sorted(filtered["station_id"].astype(str).unique().tolist())
    selected_stations = _prompt_index_selection("Estaciones disponibles", stations)
    if not selected_stations:
        raise ValueError("No stations selected.")

    filtered = filtered[filtered["station_id"].astype(str).isin(selected_stations)].copy()

    early_date = input("\nFecha inicial YYYYMMDD (Enter = sin límite): ").strip()
    late_date = input("Fecha final   YYYYMMDD (Enter = sin límite): ").strip()

    if early_date:
        early_date = _normalize_date(early_date)
        filtered = filtered[filtered["measurement_date"].astype(str) >= early_date]
    if late_date:
        late_date = _normalize_date(late_date)
        filtered = filtered[filtered["measurement_date"].astype(str) <= late_date]

    filtered = filtered.sort_values(
        ["instrument", "station_id", "measurement_date", "measurement_time"]
    ).reset_index(drop=True)

    if filtered.empty:
        raise ValueError("No measurements found with the selected filters.")

    _print_measurement_preview(filtered)

    choice = input("\nExportar todas las mediciones listadas? [s/N]: ").strip().lower()
    if choice not in {"s", "si", "sí", "y", "yes"}:
        raw = input("Ingrese números de mediciones separados por coma: ").strip()
        indices: list[int] = []
        for token in raw.split(","):
            token = token.strip()
            if not token:
                continue
            try:
                idx = int(token) - 1
                if 0 <= idx < len(filtered):
                    indices.append(idx)
            except ValueError:
                print(f"Valor ignorado: {token}")
        if not indices:
            raise ValueError("No measurements selected.")
        filtered = filtered.iloc[indices].copy().reset_index(drop=True)

    prefix = input("\nPrefijo export_id (Enter = EXP): ").strip() or "EXP"

    selection = filtered[["station_id", "measurement_date", "measurement_time", "instrument"]].copy()
    selection["export_id"] = [f"{prefix}{idx + 1:03d}" for idx in range(len(selection))]

    print("\nResumen de exportación")
    print(f"Mediciones: {len(selection)}")
    print(f"Instrumentos: {', '.join(sorted(selection['instrument'].astype(str).unique()))}")
    print(f"Estaciones: {', '.join(sorted(selection['station_id'].astype(str).unique()))}")

    confirm = input("\nContinuar con la exportación? [s/N]: ").strip().lower()
    if confirm not in {"s", "si", "sí", "y", "yes"}:
        raise ValueError("Interactive export cancelled by user.")

    output_dir = get_output_dir(sih_config)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    selection_path = output_dir / f"_interactive_selection_{timestamp}.csv"
    selection.to_csv(selection_path, index=False, encoding="utf-8-sig")

    print(f"\nSelection file generado: {selection_path}")
    return selection_path
