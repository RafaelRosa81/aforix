from __future__ import annotations

import pandas as pd
import pytest

from aforix.export.sih.ive_points import load_ive_points


def _write_points(tmp_path, rows):
    root = tmp_path / "normalized"
    root.mkdir()
    pd.DataFrame(rows).to_csv(root / "Points.csv", index=False)
    return root


def _row(station, date, time, distance, *, instrument="flowtracker", width=3.0):
    return {
        "station_id": station,
        "measurement_date": date,
        "measurement_time": time,
        "instrument": instrument,
        "distance_m": distance,
        "depth_m": 0.2,
        "velocity_mean_m_s": 0.3,
        "width_m": width,
    }


def test_selects_only_requested_measurement_and_sorts(tmp_path):
    root = _write_points(tmp_path, [
        _row("7001", "2026-01-20", "14:00:00", 2),
        _row("7002", "20260120", "140000", 1),
        _row("7001", "20260120", "140000", 1),
        _row("7001", "20260120", "140000", 0, instrument="molinete"),
        _row("7001", "20260121", "140000", 0),
    ])
    measurement = pd.Series({"station_id": "7001", "measurement_date": "20260120", "measurement_time": "140000"})
    points = load_ive_points(root, "flowtracker", measurement)
    assert points["distance_m"].tolist() == [1, 2]
    assert len(points) == 2


def test_missing_measurement_fails_instead_of_mixing_points(tmp_path):
    root = _write_points(tmp_path, [_row("7002", "20260120", "140000", 1)])
    measurement = pd.Series({"station_id": "7001", "measurement_date": "20260120", "measurement_time": "140000"})
    with pytest.raises(ValueError, match="No IVE points"):
        load_ive_points(root, "flowtracker", measurement)


def test_duplicate_distance_is_rejected(tmp_path):
    root = _write_points(tmp_path, [
        _row("7001", "20260120", "140000", 1),
        _row("7001", "20260120", "140000", 1),
    ])
    measurement = pd.Series({"station_id": "7001", "measurement_date": "20260120", "measurement_time": "140000"})
    with pytest.raises(ValueError, match="Duplicate vertical"):
        load_ive_points(root, "flowtracker", measurement)
