from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


def _load_audit_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "audit_pipeline_outputs.py"
    spec = importlib.util.spec_from_file_location("audit_pipeline_outputs", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load audit script: {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


audit_duplicates = _load_audit_module().audit_duplicates


MEASUREMENT = {
    "instrument": "flowtracker",
    "station_id": "7005",
    "measurement_date": "20251217",
    "measurement_time": "093425",
}


def test_audit_duplicates_flowtracker_distinct_percent_depth_is_not_duplicate(tmp_path):
    points_dir = tmp_path / "normalized" / "flowtracker" / "Points"
    points_dir.mkdir(parents=True)

    pd.DataFrame(
        [
            {
                **MEASUREMENT,
                "point_index": "16",
                "percent_depth": "0.2",
                "distance_m": "3.0",
                "q_m3s": "0.01",
            },
            {
                **MEASUREMENT,
                "point_index": "16",
                "percent_depth": "0.8",
                "distance_m": "3.0",
                "q_m3s": "0.02",
            },
        ]
    ).to_csv(points_dir / "7005_Points_20251217_093425.csv", index=False)

    report = audit_duplicates(tmp_path / "normalized")

    assert len(report) == 1
    assert report.loc[0, "instrument"] == "flowtracker"
    assert report.loc[0, "group"] == "Points"
    assert report.loc[0, "status"] == "ok"
    assert report.loc[0, "n_duplicated_rows"] == 0
