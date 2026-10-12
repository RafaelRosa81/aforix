"""Adapter between normalized SIH Points.csv and the IVE calculator."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from aforix.analysis.uncertainty.calculator import IVEPoint, IVEParameters, calculate_ive
from aforix.analysis.uncertainty.excel_report import write_ive_excel_report
from aforix.export.sih.ive_points import load_ive_points


def calculate_sih_ive_fields(
    normalized_root: str | Path,
    instrument: str,
    measurement: pd.Series,
    parameters: IVEParameters | None = None,
) -> dict[str, float | str]:
    """Return SIH IVE fields, preserving missing results as empty numeric cells.

    The velocity instrumental minimum is not yet supplied by the normalized
    schema, so calculated numeric results remain provisional.
    """
    empty: dict[str, float | str] = {
        "incertidumbre_IVE": "",
        "error_IVE": "",
        "calidad_IVE": "",
    }
    try:
        df = load_ive_points(normalized_root, instrument, measurement)
        points = [
            IVEPoint(
                distance_m=float(row.distance_m),
                depth_m=float(row.depth_m),
                velocity_m_s=float(row.velocity_mean_m_s),
            )
            for row in df.itertuples(index=False)
        ]
        result = calculate_ive(points, width_m=float(df["width_m"].iloc[0]), parameters=parameters)
    except (ValueError, FileNotFoundError, KeyError, TypeError, OverflowError) as exc:
        return {**empty, "calidad_IVE": f"IVE no disponible: {exc}"}

    return {
        "incertidumbre_IVE": (
            result.relative_uncertainty_pct if result.relative_uncertainty_pct is not None else ""
        ),
        "error_IVE": (
            result.absolute_uncertainty_m3s if result.absolute_uncertainty_m3s is not None else ""
        ),
        "calidad_IVE": result.quality,
    }


def write_sih_ive_report(
    normalized_root: str | Path,
    output_root: str | Path,
    instrument: str,
    measurement: pd.Series,
    parameters: IVEParameters | None = None,
) -> Path:
    """Generate an auditable report using the same normalized data and engine as SIH."""
    df = load_ive_points(normalized_root, instrument, measurement)
    points = [
        IVEPoint(
            distance_m=float(row.distance_m),
            depth_m=float(row.depth_m),
            velocity_m_s=float(row.velocity_mean_m_s),
        )
        for row in df.itertuples(index=False)
    ]
    result = calculate_ive(points, width_m=float(df["width_m"].iloc[0]))
    return write_ive_excel_report(
        output_root,
        instrument=instrument,
        station_id=measurement["station_id"],
        measurement_date=measurement["measurement_date"],
        measurement_time=measurement["measurement_time"],
        normalized_points=df,
        result=result,
        parameters=parameters,
    )
