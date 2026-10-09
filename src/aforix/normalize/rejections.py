"""Reject whole measurements with missing/non-finite point mean velocities."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from aforix.normalize.identity import KEY_COLUMNS, measurement_keys
from aforix.normalize.normalizer import normalize_table, _coalesce_sources, _get_sources
from aforix.normalize.registry import NormalizationRegistry

REPORT_COLUMNS = KEY_COLUMNS + [
    "source_file", "canonical_file", "csv_row", "point_index", "point_label",
    "distance_m", "velocity_raw", "reason",
]


def find_rejections(
    input_root: Path, instruments: list[str], registry: NormalizationRegistry,
) -> tuple[set[tuple[str, ...]], pd.DataFrame]:
    rejected: set[tuple[str, ...]] = set()
    records = []
    for instrument in instruments:
        try:
            spec = registry.get(instrument, "Points")
        except KeyError:
            continue
        if "velocity_mean_m_s" not in spec.get("columns", {}):
            continue
        concat = input_root / instrument / "Points.csv"
        paths = (
            [concat] if concat.exists()
            else sorted((input_root / instrument / "Points").glob("*.csv"))
        )
        for path in paths:
            raw = pd.read_csv(path, dtype=str)
            mapped = normalize_table(raw, spec, validate_qc=False)
            if mapped.empty:
                continue
            velocity = pd.to_numeric(mapped["velocity_mean_m_s"], errors="coerce")
            invalid = ~np.isfinite(velocity.to_numpy(dtype=float, na_value=np.nan))
            if not invalid.any():
                continue
            keys = measurement_keys(mapped)
            raw_velocity = _coalesce_sources(
                raw, _get_sources(spec["columns"]["velocity_mean_m_s"]),
            )
            for index in mapped.index[invalid]:
                key = keys.loc[index]
                rejected.add(key)
                row = mapped.loc[index]
                records.append({
                    **dict(zip(KEY_COLUMNS, key)),
                    "source_file": row.get("source_file"),
                    "canonical_file": str(path),
                    "csv_row": int(index) + 2,
                    "point_index": row.get("point_index"),
                    "point_label": row.get("point_label"),
                    "distance_m": row.get("distance_m"),
                    "velocity_raw": raw_velocity.loc[index],
                    "reason": "missing_or_non_finite_mean_velocity",
                })
    return rejected, pd.DataFrame(records, columns=REPORT_COLUMNS)


def purge_rejected_outputs(output_root: Path, rejected: set[tuple[str, ...]]) -> None:
    """Remove rejected rows even in previously generated, unselected groups."""
    groups = {"Summary", "Points", "Sections", "Gates"}
    for path in sorted(output_root.rglob("*.csv")):
        if path.stem not in groups and path.parent.name not in groups:
            continue
        frame = pd.read_csv(path, dtype=str)
        if frame.empty:
            continue
        keys = measurement_keys(frame)
        keep = ~keys.isin(rejected)
        if keep.all():
            continue
        if not keep.any():
            path.unlink()
        else:
            frame.loc[keep].to_csv(path, index=False)
