from __future__ import annotations

import pandas as pd

from aforix.validation.checks.hydraulic_consistency import run


MEASUREMENT_KEY = {
    "instrument": "flowtracker",
    "station_id": "7001",
    "measurement_date": "20260122",
    "measurement_time": "142258",
}


def _run_case(tmp_path, *, q_summary_m3s: float, q_points_m3s: list[float]):
    input_dir = tmp_path / "normalized"
    input_dir.mkdir()

    pd.DataFrame(
        [
            {
                **MEASUREMENT_KEY,
                "q_total_m3s": q_summary_m3s,
                "q_total_ls": q_summary_m3s * 1000,
                "area_total_m2": 1.0,
            }
        ]
    ).to_csv(input_dir / "Summary.csv", index=False)

    n = len(q_points_m3s)
    pd.DataFrame(
        [
            {
                **MEASUREMENT_KEY,
                "q_m3s": q,
                "q_ls": q * 1000,
                "area_m2": 1.0 / n,
            }
            for q in q_points_m3s
        ]
    ).to_csv(input_dir / "Points.csv", index=False)

    _, report = run(
        input_dir=input_dir,
        output_dir=tmp_path / "validation",
        validation_cfg={
            "keys": list(MEASUREMENT_KEY),
            "hydraulic_consistency": {
                "q_tolerance_pct": 1.0,
                "q_tolerance_abs_ls": 0.5,
                "area_tolerance_pct": 1.0,
            },
        },
    )
    return report.iloc[0]


def test_val02_zero_summary_and_zero_points_is_ok(tmp_path):
    row = _run_case(tmp_path, q_summary_m3s=0.0, q_points_m3s=[0.0])

    assert row["status"] == "ok"
    assert bool(row["q_ok"])


def test_val02_accepts_difference_within_absolute_tolerance(tmp_path):
    # 0.4 L/s differs by 4%, but is within the configured 0.5 L/s floor.
    row = _run_case(tmp_path, q_summary_m3s=0.0100, q_points_m3s=[0.0104])

    assert abs(row["q_diff_ls"] - 0.4) < 1e-9
    assert row["q_rel_diff_pct"] > 1.0
    assert row["status"] == "ok"
    assert bool(row["q_ok"])


def test_val02_accepts_difference_within_relative_tolerance(tmp_path):
    # 6 L/s exceeds the absolute tolerance, but 0.6% is within 1%.
    row = _run_case(tmp_path, q_summary_m3s=1.000, q_points_m3s=[1.006])

    assert abs(row["q_diff_ls"]) > 0.5
    assert abs(row["q_rel_diff_pct"]) <= 1.0
    assert row["status"] == "ok"
    assert bool(row["q_ok"])


def test_val02_rejects_difference_exceeding_both_tolerances(tmp_path):
    # 0.6 L/s and 6% exceed both configured tolerances.
    row = _run_case(tmp_path, q_summary_m3s=0.0100, q_points_m3s=[0.0106])

    assert abs(row["q_diff_ls"]) > 0.5
    assert abs(row["q_rel_diff_pct"]) > 1.0
    assert row["status"] == "inconsistent"
    assert not bool(row["q_ok"])
