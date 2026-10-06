from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


def _load_audit_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "audit_pipeline_outputs.py"
    spec = importlib.util.spec_from_file_location("audit_pipeline_outputs", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load audit script: {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
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



def test_audit_duplicates_flowtracker_same_percent_depth_is_duplicate(tmp_path):
    points_dir = tmp_path / "normalized" / "flowtracker" / "Points"
    points_dir.mkdir(parents=True)

    row = {
        **MEASUREMENT,
        "point_index": "16",
        "percent_depth": "0.2",
        "distance_m": "3.0",
        "q_m3s": "0.01",
    }
    pd.DataFrame([row, row]).to_csv(
        points_dir / "7005_Points_20251217_093425.csv",
        index=False,
    )

    report = audit_duplicates(tmp_path / "normalized")

    assert len(report) == 1
    assert report.loc[0, "status"] == "duplicates"
    assert report.loc[0, "n_duplicated_rows"] == 2
    assert report.loc[0, "n_duplicate_keys"] == 1

def test_audit_duplicates_percent_depth_key_is_instrument_name_agnostic(tmp_path):
    points_dir = tmp_path / "normalized" / "flowtracker_alias" / "Points"
    points_dir.mkdir(parents=True)

    measurement = {
        **MEASUREMENT,
        "instrument": "FT",
    }
    pd.DataFrame(
        [
            {
                **measurement,
                "point_index": "16",
                "percent_depth": "0.2",
                "distance_m": "3.0",
                "q_m3s": "0.01",
            },
            {
                **measurement,
                "point_index": "16",
                "percent_depth": "0.8",
                "distance_m": "3.0",
                "q_m3s": "0.02",
            },
        ]
    ).to_csv(points_dir / "7005_Points_20251217_093425.csv", index=False)

    report = audit_duplicates(tmp_path / "normalized")

    assert len(report) == 1
    assert report.loc[0, "status"] == "ok"
    assert report.loc[0, "n_duplicated_rows"] == 0
    assert "percent_depth" in report.loc[0, "key_columns_used"].split(";")

