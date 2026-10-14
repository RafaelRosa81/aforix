from pathlib import Path

import pandas as pd
import pytest

from aforix.normalize.run import (
    _flowtracker_hydraulic_radius,
    _enrich_flowtracker_summary_hydraulic_radius,
)


def test_rectangular_section_includes_vertical_banks():
    points = pd.DataFrame({"distance_m": [0, 2, 4], "depth_m": [1, 1, 1]})
    # A=4 m2; P=4 m bottom + 2 m vertical banks.
    assert _flowtracker_hydraulic_radius(points) == pytest.approx(4 / 6)


def test_zero_depth_banks_use_sloping_bed():
    points = pd.DataFrame({"distance_m": [0, 2, 4], "depth_m": [0, 2, 0]})
    # A=4 m2; P=2*sqrt(8) m.
    assert _flowtracker_hydraulic_radius(points) == pytest.approx(4 / (2 * 8**0.5))


@pytest.mark.parametrize("positions,depths", [
    ([0, 0, 2], [0, 1, 0]),
    ([0, 2], [0, 0]),
    ([0, 2], [1, None]),
    ([0, 2], [1, -1]),
])
def test_invalid_geometry_rejected(positions, depths):
    with pytest.raises(ValueError):
        _flowtracker_hydraulic_radius(
            pd.DataFrame({"distance_m": positions, "depth_m": depths})
        )


def test_radius_is_joined_by_measurement_not_station_alone(tmp_path: Path):
    path = tmp_path / "Summary.csv"
    summary = pd.DataFrame({
        "instrument": ["flowtracker", "flowtracker"],
        "station_id": ["7013", "7013"],
        "measurement_date": ["20260123", "20260123"],
        "measurement_time": ["100854", "120233"],
    })
    summary.to_csv(path, index=False)
    points = pd.DataFrame({
        "instrument": ["flowtracker"] * 4,
        "station_id": ["7013"] * 4,
        "measurement_date": ["20260123"] * 4,
        "measurement_time": ["100854", "100854", "120233", "120233"],
        "distance_m": [0, 4, 0, 4],
        "depth_m": [1, 1, 2, 2],
    })
    result = _enrich_flowtracker_summary_hydraulic_radius(
        summary_paths=[path], points_frames=[points]
    )
    assert result[0]["hydraulic_radius_m"].tolist() == pytest.approx([4 / 6, 8 / 8])
    assert pd.read_csv(path)["hydraulic_radius_m"].tolist() == pytest.approx([4 / 6, 1])
