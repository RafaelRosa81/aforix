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


def test_m9_reads_points_directory_and_deduplicates_renamed_exports(tmp_path):
    root = tmp_path / "normalized"
    points_dir = root / "m9" / "Points"
    points_dir.mkdir(parents=True)
    rows = [
        {
            **_row("133", "20260703", "111721", 1.0, instrument="m9", width=12.0),
            "source_file": r"C:\data\transect.mat",
            "sample_number": 1,
        },
        {
            **_row("133", "20260703", "111721", 2.0, instrument="m9", width=12.0),
            "source_file": r"C:\data\transect.mat",
            "sample_number": 2,
        },
    ]
    pd.DataFrame(rows).to_csv(points_dir / "new_filename_Points.csv", index=False)
    pd.DataFrame(rows).to_csv(points_dir / "legacy_filename.csv", index=False)

    # The cross-instrument concat can be stale; instrument-specific file rows
    # are preferred when they exist.
    stale = pd.DataFrame([{
        **_row("133", "20260703", "111721", 1.0, instrument="m9", width=12.0),
        "distance_m": "",
    }])
    stale.to_csv(root / "Points.csv", index=False)

    measurement = pd.Series({
        "station_id": "133",
        "measurement_date": "20260703",
        "measurement_time": "111721",
        "source_file": r"C:\data\transect.mat",
    })
    points = load_ive_points(root, "m9", measurement)

    assert points["distance_m"].tolist() == [1.0, 2.0]
    assert points["sample_number"].tolist() == ["1", "2"]


def test_m9_rejects_conflicting_duplicate_sample_exports(tmp_path):
    root = tmp_path / "normalized"
    points_dir = root / "m9" / "Points"
    points_dir.mkdir(parents=True)
    base = {
        **_row("133", "20260703", "111721", 1.0, instrument="m9", width=12.0),
        "source_file": "transect.mat",
        "sample_number": 1,
    }
    pd.DataFrame([base]).to_csv(points_dir / "copy_a.csv", index=False)
    pd.DataFrame([{**base, "depth_m": 0.9}]).to_csv(points_dir / "copy_b.csv", index=False)

    measurement = pd.Series({
        "station_id": "133",
        "measurement_date": "20260703",
        "measurement_time": "111721",
        "source_file": "transect.mat",
    })
    with pytest.raises(ValueError, match="Conflicting duplicate M9 Points"):
        load_ive_points(root, "m9", measurement)


def test_m9_prefers_complete_copy_over_legacy_rows_with_missing_ive_fields(tmp_path):
    root = tmp_path / "normalized"
    points_dir = root / "m9" / "Points"
    points_dir.mkdir(parents=True)
    complete = {
        **_row("133", "20260703", "111721", 1.0, instrument="m9", width=12.0),
        "source_file": "transect.mat",
        "sample_number": 1,
    }
    incomplete = {**complete, "distance_m": "", "velocity_mean_m_s": ""}
    # Lexical ordering places the legacy copy first, exercising selection rather
    # than relying on whichever duplicate filename happens to sort first.
    pd.DataFrame([incomplete]).to_csv(points_dir / "a_legacy.csv", index=False)
    pd.DataFrame([complete]).to_csv(points_dir / "z_complete.csv", index=False)

    measurement = pd.Series({
        "station_id": "133",
        "measurement_date": "20260703",
        "measurement_time": "111721",
        "source_file": "transect.mat",
    })
    points = load_ive_points(root, "m9", measurement)

    assert points["distance_m"].tolist() == [1.0]
    assert points["velocity_mean_m_s"].tolist() == [0.3]


def test_m9_rejects_points_from_another_source(tmp_path):
    rows = [{**_row('133', '20260703', '111721', i, instrument='m9'),
             'source_file': 'other.mat', 'sample_number': i} for i in [1, 2]]
    root = _write_points(tmp_path, rows)
    measurement = pd.Series({'station_id': '133', 'measurement_date': '20260703',
                             'measurement_time': '111721', 'source_file': 'requested.mat'})
    with pytest.raises(ValueError, match='source_file does not match'):
        load_ive_points(root, 'm9', measurement)
