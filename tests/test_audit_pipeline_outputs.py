from __future__ import annotations

import pandas as pd

from scripts.audit_pipeline_outputs import audit_duplicates


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
