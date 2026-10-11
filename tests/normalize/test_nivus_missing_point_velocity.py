from pathlib import Path

import pandas as pd
import pytest
import yaml

from aforix.normalize.normalizer import normalize_table


SPEC_PATH = Path(__file__).resolve().parents[2] / "configs" / "normalization" / "nivus.yaml"


def _points_spec():
    return yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))["tables"]["Points"]


def test_nivus_points_keep_missing_velocities_and_valid_depths():
    raw = pd.DataFrame({
        "station_id": ["7001", "7001", "7001"],
        "measurement_date": ["20250711"] * 3,
        "measurement_time": ["151429"] * 3,
        "instrument": ["nivus"] * 3,
        "index": ["1", "2", "3"],
        "pos [m]": ["0.0", "3.4615", "7.3002"],
        "width_m": ["7.3"] * 3,
        "h [m]": ["0.10", "0.0397", "#-1"],
        "v [m/s]": ["0.125", "#-1", "#-1"],
        "percent_q": ["10", "0", "0"],
    })
    result = normalize_table(raw, _points_spec())

    assert len(result) == 3
    assert result["point_index"].tolist() == [1, 2, 3]
    assert result.loc[0, "velocity_mean_m_s"] == pytest.approx(0.125)
    assert pd.isna(result.loc[1, "velocity_mean_m_s"])
    assert result.loc[1, "depth_m"] == pytest.approx(0.0397)
    assert pd.isna(result.loc[2, "velocity_mean_m_s"])
    assert pd.isna(result.loc[2, "depth_m"])


def test_nivus_points_zero_velocity_remains_zero():
    raw = pd.DataFrame({
        "station_id": ["7092"],
        "measurement_date": ["20250724"],
        "measurement_time": ["134631"],
        "instrument": ["nivus"],
        "index": ["1"],
        "pos [m]": ["0.6239"],
        "width_m": ["2.7"],
        "h [m]": ["0.2"],
        "v [m/s]": ["0.0"],
        "percent_q": ["0"],
    })
    result = normalize_table(raw, _points_spec())
    assert result.loc[0, "velocity_mean_m_s"] == pytest.approx(0.0)
