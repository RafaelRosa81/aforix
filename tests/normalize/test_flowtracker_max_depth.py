from pathlib import Path

import pandas as pd
import pytest

from aforix.normalize.run import _enrich_flowtracker_summary_max_depth


def _frame(station, time, depths):
    return pd.DataFrame({
        "instrument": ["flowtracker"] * len(depths),
        "station_id": [station] * len(depths),
        "measurement_date": ["20260123"] * len(depths),
        "measurement_time": [time] * len(depths),
        "depth_m": depths,
    })


def test_flowtracker_max_depth_is_per_measurement(tmp_path: Path):
    summary_path = tmp_path / "Summary.csv"
    summary = pd.DataFrame({
        "instrument": ["flowtracker", "flowtracker"],
        "station_id": ["7013", "7014"],
        "measurement_date": ["20260123", "20260123"],
        "measurement_time": ["100854", "120233"],
        "depth_mean_m": [0.13, 0.161],
    })
    summary.to_csv(summary_path, index=False)
    points = pd.concat([
        _frame("7013", "100854", [0.10, 0.25, None]),
        _frame("7014", "120233", [0.15, 0.31]),
    ], ignore_index=True)

    result = _enrich_flowtracker_summary_max_depth(
        summary_paths=[summary_path], points_frames=[points]
    )
    assert result[0]["max_depth_m"].tolist() == pytest.approx([0.25, 0.31])
    assert result[0]["depth_mean_m"].tolist() == pytest.approx([0.13, 0.161])
    saved = pd.read_csv(summary_path)
    assert saved["max_depth_m"].tolist() == pytest.approx([0.25, 0.31])


def test_flowtracker_max_depth_rejects_unmatched_measurement(tmp_path: Path):
    summary_path = tmp_path / "Summary.csv"
    _frame("7013", "100854", [0.10]).drop(columns="depth_m").to_csv(
        summary_path, index=False
    )
    with pytest.raises(ValueError, match="without matching Points depth"):
        _enrich_flowtracker_summary_max_depth(
            summary_paths=[summary_path],
            points_frames=[_frame("7014", "120233", [0.25])],
        )


def test_flowtracker_max_depth_rejects_duplicate_summary_keys(tmp_path: Path):
    summary_path = tmp_path / "Summary.csv"
    pd.concat([_frame("7013", "100854", [0.1]).drop(columns="depth_m")] * 2).to_csv(
        summary_path, index=False
    )
    with pytest.raises(ValueError, match="Duplicate FlowTracker Summary"):
        _enrich_flowtracker_summary_max_depth(
            summary_paths=[summary_path],
            points_frames=[_frame("7013", "100854", [0.25])],
        )
