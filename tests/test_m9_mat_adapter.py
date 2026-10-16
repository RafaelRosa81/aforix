from datetime import datetime

import numpy as np
import pandas as pd
import yaml
from scipy.io import savemat

from aforix.export.sih.ive_integration import prepare_sih_ive
from aforix.ingest.adapters.m9_mat import parse_m9_mat
from aforix.ingest.adapters.m9_mat import _distance_from_left_bank
from aforix.normalize.normalizer import normalize_table


def test_m9_distance_from_left_bank_accounts_for_track_backtracking():
    distance = _distance_from_left_bank(np.array([0.0, 2.0, -0.2, np.nan]), 1.0)

    assert np.allclose(distance[:3], [1.2, 3.2, 1.0])
    assert np.isnan(distance[3])


def test_parse_m9_mat_summary_and_sample_points(tmp_path):
    path = tmp_path / "20260703113024r.mat"
    savemat(
        path,
        {
            "SiteInfo": {"Station_Number": "133.0", "Site_Name": "Pasarela", "Comments": "test"},
            "SystemHW": {"SerialNumber": "4980", "FirmwareVersion": 4},
            "System": {
                "Time": np.array([836393424.0, 836393425.0]),
                "Temperature": np.array([8.3, 8.4]),
                "Heading": np.array([10.0, 11.0]),
            },
            "Summary": {
                "Total_Q": np.array([1.0, 5.0]),
                "Area": 32.0,
                "Depth": np.array([0.8, 1.0]),
                "Track": np.array([[0.0, 0.0], [3.0, 4.0]]),
                "Mean_Vel": np.array([[0.1, 0.2], [0.2, 0.3]]),
                "Boat_Vel": np.zeros((2, 4)),
            },
            "Setup": {
                "Edges_0__DistanceToBank": 1.0,
                "Edges_1__DistanceToBank": 1.5,
                "coordinateSystem": 2,
            },
            "GPS": {"Latitude": np.array([-34.4, -34.5]), "Longitude": np.array([-56.3, -56.4])},
            "Compass": {"Pitch": np.array([0.1, 0.2]), "Roll": np.array([0.3, 0.4])},
        },
    )

    parsed = parse_m9_mat(path, timezone_name="UTC")
    summary = parsed["summary"]
    assert summary["station_id"] == "133.0"
    assert summary["q_total_m3s"] == 5.0
    assert summary["area_total_m2"] == 32.0
    assert np.isclose(summary["wetted_perimeter_m"], np.hypot(1.0, 0.8) + np.hypot(5.0, 0.2) + np.hypot(1.5, 1.0))
    assert np.isclose(summary["hydraulic_radius_m"], 32.0 / summary["wetted_perimeter_m"])
    assert summary["hydraulic_radius_method"] == "summary_area_over_profile_wetted_perimeter"
    assert summary["velocity_mean_m_s"] == 5.0 / 32.0
    assert summary["width_total_m"] == 7.5
    assert summary["measurement_start"] == datetime.fromisoformat("2026-07-03T11:30:24+00:00")
    assert len(parsed["points"]) == 2
    assert parsed["points"][1]["q_increment_m3s"] == 4.0
    assert parsed["points"][1]["distance_along_transect_m"] == 5.0
    assert parsed["points"][0]["distance_m"] == 1.0
    assert parsed["points"][1]["distance_m"] == 6.0
    assert np.isclose(parsed["points"][0]["normal_velocity_m_s"], 0.04)
    assert np.isclose(parsed["points"][1]["normal_velocity_m_s"], 0.02)
    assert np.isclose(parsed["points"][0]["velocity_mean_m_s"], 0.04)
    assert np.isclose(parsed["points"][1]["velocity_mean_m_s"], 0.02)


def test_m9_normalization_produces_sih_hydraulic_columns():
    with open("configs/normalization/m9.yaml", encoding="utf-8") as f:
        spec = yaml.safe_load(f)["tables"]["Summary"]
    raw = pd.DataFrame(
        [{
            "station_id": "133", "station_name": "Pasarela", "measurement_date": "20260703",
            "measurement_time": "113024", "instrument": "m9", "source_file": "x.mat",
            "source_run_dir": "run", "run_id": "run", "q_total_m3s": 5.0,
            "area_total_m2": 32.0, "width_total_m": 31.0, "depth_mean_m": 0.9,
            "wetted_perimeter_m": 25.0, "hydraulic_radius_m": 1.28,
            "hydraulic_radius_method": "summary_area_over_profile_wetted_perimeter",
            "velocity_mean_m_s": 5.0 / 32.0, "measurement_end_date": "20260703",
            "measurement_end_time": "113241",
        }]
    )
    normalized = normalize_table(raw, spec)
    assert normalized.loc[0, "q_total_m3s"] == 5.0
    assert normalized.loc[0, "q_total_ls"] == 5000.0
    assert normalized.loc[0, "area_total_m2"] == 32.0
    assert normalized.loc[0, "hydraulic_radius_m"] == 1.28
    assert normalized.loc[0, "instrument"] == "m9"


def test_m9_normalized_points_feed_sih_ive(tmp_path):
    with open("configs/normalization/m9.yaml", encoding="utf-8") as f:
        spec = yaml.safe_load(f)["tables"]["Points"]
    raw = pd.DataFrame([
        {
            "station_id": "133",
            "station_name": "Pasarela",
            "measurement_date": "20260703",
            "measurement_time": "113024",
            "instrument": "m9",
            "source_file": "transect.mat",
            "source_run_dir": "run",
            "run_id": "run",
            "sample_number": i + 1,
            "timestamp": "2026-07-03T11:30:24+00:00",
            "elapsed_seconds": float(i),
            "distance_along_transect_m": float(i + 1),
            "distance_m": float(i + 0.5),
            "width_m": 12.0,
            "track_x_m": float(i),
            "track_y_m": 0.0,
            "depth_m": 1.0 + 0.05 * np.sin(i),
            "q_cumulative_m3s": float(i),
            "q_increment_m3s": 0.0,
            "mean_velocity_x_m_s": 0.2,
            "mean_velocity_y_m_s": 0.0,
            "normal_velocity_m_s": 0.2 + 0.02 * np.cos(i),
            "velocity_mean_m_s": 0.2 + 0.02 * np.cos(i),
            "boat_velocity_x_m_s": 0.0,
            "boat_velocity_y_m_s": 0.0,
            "temperature_c": 8.0,
            "heading_deg": 0.0,
            "pitch_deg": 0.0,
            "roll_deg": 0.0,
            "latitude": -34.4,
            "longitude": -56.3,
        }
        for i in range(12)
    ])
    normalized = normalize_table(raw, spec)
    points_dir = tmp_path / "m9"
    points_dir.mkdir()
    normalized.to_csv(points_dir / "Points.csv", index=False)

    measurement = pd.Series({
        "station_id": "133",
        "measurement_date": "20260703",
        "measurement_time": "113024",
    })
    selected, result = prepare_sih_ive(tmp_path, "m9", measurement)

    assert list(selected["distance_m"]) == [i + 0.5 for i in range(12)]
    assert selected["velocity_mean_m_s"].notna().all()
    assert result.status == "calculated"
    assert result.vertical_count == 12
