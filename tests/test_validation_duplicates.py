from __future__ import annotations

import pandas as pd

from aforix.validation.checks.duplicates import run


MEASUREMENT_KEY = {
    "instrument": "flowtracker",
    "station_id": "7001",
    "measurement_date": "20260122",
    "measurement_time": "142258",
}


def _write_points(tmp_path, rows):
    input_dir = tmp_path / "normalized"
    input_dir.mkdir()
    pd.DataFrame(rows).to_csv(input_dir / "Points.csv", index=False)
    return input_dir


def _validation_cfg():
    return {
        "keys": [
            "instrument",
            "station_id",
            "measurement_date",
            "measurement_time",
        ]
    }


def test_points_with_distinct_point_index_are_not_duplicates(tmp_path):
    input_dir = _write_points(
        tmp_path,
        [
            {**MEASUREMENT_KEY, "point_index": "1", "percent_depth": "0.6", "q_m3s": "0.01"},
            {**MEASUREMENT_KEY, "point_index": "2", "percent_depth": "0.6", "q_m3s": "0.02"},
        ],
    )

    _, report = run(
        input_dir=input_dir,
        output_dir=tmp_path / "validation",
        validation_cfg=_validation_cfg(),
    )

    assert report.empty


def test_flowtracker_same_vertical_at_distinct_percent_depth_is_not_duplicate(tmp_path):
    input_dir = _write_points(
        tmp_path,
        [
            {
                **MEASUREMENT_KEY,
                "point_index": "16",
                "percent_depth": "0.2",
                "measured_depth_m": "0.232",
                "q_m3s": "0.0044",
            },
            {
                **MEASUREMENT_KEY,
                "point_index": "16",
                "percent_depth": "0.8",
                "measured_depth_m": "0.058",
                "q_m3s": "0.0000",
            },
        ],
    )

    _, report = run(
        input_dir=input_dir,
        output_dir=tmp_path / "validation",
        validation_cfg=_validation_cfg(),
    )

    assert report.empty


def test_flowtracker_same_vertical_and_percent_depth_is_duplicate(tmp_path):
    input_dir = _write_points(
        tmp_path,
        [
            {
                **MEASUREMENT_KEY,
                "point_index": "16",
                "percent_depth": "0.2",
                "measured_depth_m": "0.232",
                "q_m3s": "0.0044",
            },
            {
                **MEASUREMENT_KEY,
                "point_index": "16",
                "percent_depth": "0.2",
                "measured_depth_m": "0.232",
                "q_m3s": "0.0044",
            },
        ],
    )

    _, report = run(
        input_dir=input_dir,
        output_dir=tmp_path / "validation",
        validation_cfg=_validation_cfg(),
    )

    assert len(report) == 1
    assert report.loc[0, "table"] == "Points"
    assert report.loc[0, "status"] == "duplicate"
    assert report.loc[0, "point_index"] == "16"
    assert report.loc[0, "percent_depth"] == "0.2"
    assert report.loc[0, "duplicate_count"] == 2
