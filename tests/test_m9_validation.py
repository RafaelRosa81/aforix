from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import yaml
from aforix.validation.m9 import validate_m9, split_instruments
from aforix.validation.run import run_validation


def frames():
    identity = dict(instrument="m9", station_id="133", measurement_date="20260703",
                    measurement_time="111721", source_file="transect.mat")
    summary = pd.DataFrame([{**identity, "q_total_m3s": .5, "area_total_m2": 3.,
        "width_total_m": 4., "sample_count": 2, "wetted_perimeter_m": 5.,
        "hydraulic_radius_m": .6}])
    points = pd.DataFrame([{**identity, "sample_number": i + 1, "distance_m": i + 1.,
        "width_m": 4., "depth_m": 1., "velocity_mean_m_s": .2,
        "q_cumulative_m3s": q, "q_increment_m3s": dq}
        for i, (q, dq) in enumerate([(.2, .2), (.5, .3)])])
    return summary, points


def test_m9_does_not_require_discrete_instrument_columns():
    assert validate_m9(*frames()).empty


@pytest.mark.parametrize("column,value,rule", [
    ("depth_m", -1, "range"), ("velocity_mean_m_s", np.inf, "finite"),
    ("distance_m", 5, "position"), ("width_m", 3, "width"),
    ("sample_number", 3, "sample_sequence"), ("q_increment_m3s", 9, "increments"),
    ("q_cumulative_m3s", 9, "discharge"),
])
def test_m9_invalid_samples_are_reported(column, value, rule):
    s, p = frames()
    p.loc[1, column] = value
    report = validate_m9(s, p)
    assert rule in set(report["rule"])
    assert report.message.str.contains("Que sucede:").all()
    assert report.message.str.contains("Razon:").all()
    assert report.message.str.contains("Accion:").all()


def test_m9_missing_pairs_duplicates_counts_and_radius():
    s, p = frames()
    s.loc[0, "hydraulic_radius_m"] = .9
    s.loc[0, "sample_count"] = 4
    p = pd.concat([p, p.iloc[[0]]], ignore_index=True)
    assert {"radius", "sample_count", "duplicate"} <= set(validate_m9(s, p)["rule"])
    p["source_file"] = "other.mat"
    assert "missing_pair" in set(validate_m9(s, p)["rule"])


def test_m9_missing_columns_and_missing_table():
    s, p = frames()
    assert "missing_columns" in set(validate_m9(s, p.drop(columns="depth_m"))["rule"])
    assert "missing_table" in set(validate_m9(s, None)["rule"])


def test_split_keeps_other_instruments_and_leaves_inputs_unchanged(tmp_path):
    source, temporary = tmp_path / "input", tmp_path / "temp"
    source.mkdir(); temporary.mkdir()
    s, p = frames()
    for name, frame in [("Summary", s), ("Points", p)]:
        other = frame.assign(instrument="flowtracker")
        pd.concat([frame, other]).to_csv(source / f"{name}.csv", index=False)
    path, has_other, report = split_instruments(source, temporary)
    assert path == temporary and has_other and report.empty
    assert set(pd.read_csv(path / "Points.csv")["instrument"]) == {"flowtracker"}
    assert set(pd.read_csv(source / "Points.csv")["instrument"]) == {"flowtracker", "m9"}


def test_validation_command_reports_m9_without_false_missing_columns(tmp_path):
    source = tmp_path / "input"; source.mkdir()
    output = tmp_path / "output"
    s, p = frames()
    s.to_csv(source / "Summary.csv", index=False)
    p.to_csv(source / "Points.csv", index=False)
    config = tmp_path / "main.yaml"
    config.write_text(yaml.safe_dump({"project": {"name": "m9-test"},
        "paths": {key: str(tmp_path) for key in ("raw_data_dir", "runs_root", "database_root")},
        "validation": {
        "input_dir": str(source), "output_dir": str(output),
        "required_columns": {"Points": ["point_index", "area_m2", "q_m3s"]},
    }}))
    run_validation(config)
    result = pd.read_csv(output / "validation_summary.csv")
    assert result["check"].tolist() == ["m9"]
    assert result["status"].tolist() == ["ok"]
    p.loc[0, "depth_m"] = -1
    p.to_csv(source / "Points.csv", index=False)
    run_validation(config)
    assert pd.read_csv(output / "validation_summary.csv")["status"].tolist() == ["issues_found"]


def test_no_m9_preserves_existing_input_path(tmp_path):
    temporary = tmp_path / "temp"; temporary.mkdir()
    s, p = frames()
    for name, frame in [("Summary", s), ("Points", p)]:
        frame.assign(instrument="molinete").to_csv(tmp_path / f"{name}.csv", index=False)
    path, has_other, report = split_instruments(tmp_path, temporary)
    assert path == tmp_path and has_other and report is None


def test_missing_distances_do_not_claim_repeated_positions():
    summary, points = frames()
    points["distance_m"] = np.nan
    report = validate_m9(summary, points)
    assert "finite" in set(report.rule)
    assert "ive_positions" not in set(report.rule)
