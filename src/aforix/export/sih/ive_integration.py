"""Adapter between normalized SIH Points.csv and the IVE calculator."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from aforix.analysis.uncertainty.calculator import (
    IVEPoint,
    IVEParameters,
    IVECalculation,
    calculate_ive,
)
from aforix.analysis.uncertainty.excel_report import write_ive_excel_report
from aforix.export.sih.ive_points import load_ive_points


def _calculate_sih_ive(
    normalized_root: str | Path,
    instrument: str,
    measurement: pd.Series,
    parameters: IVEParameters | None = None,
) -> tuple[pd.DataFrame, IVECalculation]:
    """Load normalized points and calculate IVE using one shared path."""
    df = load_ive_points(normalized_root, instrument, measurement)
    points = [
        IVEPoint(
            distance_m=float(row.distance_m),
            depth_m=float(row.depth_m),
            velocity_m_s=float(row.velocity_mean_m_s),
        )
        for row in df.itertuples(index=False)
    ]
    effective_parameters = parameters if parameters is not None else IVEParameters(
        left_bank_mode="preserve_depth"
    )
    result = calculate_ive(
        points,
        width_m=float(df["width_m"].iloc[0]),
        parameters=effective_parameters,
    )
    return df, result


def prepare_sih_ive(
    normalized_root: str | Path,
    instrument: str,
    measurement: pd.Series,
    parameters: IVEParameters | None = None,
) -> tuple[pd.DataFrame, IVECalculation]:
    """Prepare a single reusable IVE calculation for SIH export."""
    return _calculate_sih_ive(
        normalized_root,
        instrument,
        measurement,
        parameters,
    )


def calculate_sih_ive_fields(
    normalized_root: str | Path,
    instrument: str,
    measurement: pd.Series,
    parameters: IVEParameters | None = None,
) -> dict[str, float | str]:
    """Return SIH IVE fields, leaving unavailable numeric results empty.

    The current project methodology uses the IVE velocity standard deviation
    directly, without applying an additional instrumental minimum.
    """
    empty: dict[str, float | str] = {
        "incertidumbre_IVE": "",
        "error_IVE": "",
        "calidad_IVE": "",
    }
    try:
        _, result = _calculate_sih_ive(
            normalized_root, instrument, measurement, parameters
        )
    except (ValueError, FileNotFoundError, KeyError, TypeError, OverflowError) as exc:
        return {**empty, "calidad_IVE": f"IVE no disponible: {exc}"}

    return _sih_fields_from_ive_result(result)


def write_sih_ive_report(
    normalized_root: str | Path,
    output_root: str | Path,
    instrument: str,
    measurement: pd.Series,
    parameters: IVEParameters | None = None,
    prepared: tuple[pd.DataFrame, IVECalculation] | None = None,
) -> Path:
    """Generate an auditable report using the same normalized data and engine as SIH."""
    df, result = (
        prepared
        if prepared is not None
        else _calculate_sih_ive(
            normalized_root, instrument, measurement, parameters
        )
    )
    effective_parameters = parameters if parameters is not None else IVEParameters(
        left_bank_mode="preserve_depth"
    )
    return write_ive_excel_report(
        output_root,
        instrument=instrument,
        station_id=measurement["station_id"],
        measurement_date=measurement["measurement_date"],
        measurement_time=measurement["measurement_time"],
        normalized_points=df,
        result=result,
        parameters=effective_parameters,
    )

def _sih_fields_from_ive_result(result: IVECalculation) -> dict[str, float | str]:
    """Convert an existing IVE result to the official SIH fields."""
    return {
        "incertidumbre_IVE": (
            result.relative_uncertainty_pct
            if result.relative_uncertainty_pct is not None else ""
        ),
        "error_IVE": (
            result.absolute_uncertainty_m3s
            if result.absolute_uncertainty_m3s is not None else ""
        ),
        "calidad_IVE": result.quality,
    }
