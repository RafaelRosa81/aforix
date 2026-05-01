from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

CorrelationKind = Literal[
    "gauges_vs_model",
    "gauges_vs_stations",
    "model_vs_stations",
]
TimeStep = Literal["hourly", "daily", "monthly"]


@dataclass(frozen=True)
class MeasuringInstrument:
    """Measurement instrument definition loaded from config."""

    code: str
    name: str
    subdir: str
    summary_format: str = "wide"
    flow_column: str | None = None
    flow_unit: str = "l/s"
    flow_row_label: str | None = None
    time_row_label: str | None = None


@dataclass(frozen=True)
class RegressionSpec:
    """Explicit X/Y semantic definition for a correlation workflow."""

    x_label: str
    y_label: str
    x_column: str
    y_column: str
    equation_label: str


@dataclass(frozen=True)
class CorrelationPair:
    """Generic station/point pair."""

    station_id: str
    point_id: str


@dataclass(frozen=True)
class CorrelationPaths:
    """Resolved input/output paths for correlation workflows."""

    normalized_root: Path
    external_model_dir: Path
    external_stations_dir: Path
    output_root: Path
