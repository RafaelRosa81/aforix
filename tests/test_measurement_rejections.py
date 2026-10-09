from pathlib import Path

import pandas as pd
import pytest
import yaml

from aforix.normalize.registry import NormalizationRegistry
from aforix.normalize.normalizer import normalize_table
from aforix.normalize.rejections import find_rejections, measurement_keys
from aforix.normalize.run import normalize_database
import aforix.normalize.run as runner

ROOT = Path(__file__).resolve().parents[1]


def points(velocity, station="BAD"):
    return pd.DataFrame({
        "instrument": ["nivus"] * 2, "station_id": [station] * 2,
        "measurement_date": ["20250711"] * 2, "measurement_time": ["151429"] * 2,
        "source_file": [f"{station}.xml"] * 2, "index": [1, 2],
        "pos [m]": [1, 2], "h [m]": [1, 1], "v [m/s]": ["0", velocity],
    })


@pytest.mark.parametrize("velocity", ["#-1", "", None, "inf", "-inf", "NaN"])
def test_missing_velocity_rejects_entire_measurement(tmp_path, velocity):
    folder = tmp_path / "nivus" / "Points"
    folder.mkdir(parents=True)
    points(velocity).to_csv(folder / "bad.csv", index=False)
    registry = NormalizationRegistry(ROOT / "configs/normalization")
    rejected, report = find_rejections(tmp_path, ["nivus"], registry)
    assert len(rejected) == 1
    assert len(report) == 1
    assert report.iloc[0].point_index == 2
    assert report.iloc[0].csv_row == 3
    assert normalize_table(points(velocity), registry.get("nivus", "Points"), excluded_measurements=rejected).empty


@pytest.mark.parametrize("velocity", ["0", "-1", "-0,3", "0.5"])
def test_finite_velocity_including_zero_and_negative_is_valid(tmp_path, velocity):
    folder = tmp_path / "nivus" / "Points"
    folder.mkdir(parents=True)
    points(velocity).to_csv(folder / "good.csv", index=False)
    rejected, report = find_rejections(tmp_path, ["nivus"], NormalizationRegistry(ROOT / "configs/normalization"))
    assert not rejected
    assert report.empty


@pytest.mark.parametrize("layout", ["concat", "files"])
@pytest.mark.parametrize("points_only", [False, True])
def test_pipeline_filters_all_groups_and_stale_outputs(tmp_path, monkeypatch, layout, points_only):
    raw = tmp_path / "raw"
    output = tmp_path / "normalized"
    source = raw / "nivus"
    source.mkdir(parents=True)
    valid = points("-0.5", "GOOD")
    invalid = points("#-1")
    frames = {"Points": pd.concat([valid, invalid], ignore_index=True)}
    meta = valid.iloc[[0]][["instrument", "station_id", "measurement_date", "measurement_time", "source_file"]]
    meta = pd.concat([meta, invalid.iloc[[0]][meta.columns]], ignore_index=True)
    frames["Summary"] = meta.assign(**{"w [m]": 3, "q [l/s]": 100})
    frames["Sections"] = pd.concat([meta.assign(index=i, **{"pos [m]": i, "w [m]": 1, "h [m]": 1, "q [l/s]": 25, "factor [%]": 25}) for i in range(1, 5)], ignore_index=True)
    frames["Gates"] = meta.assign(index=1)
    for group, frame in frames.items():
        if layout == "concat":
            frame.to_csv(source / f"{group}.csv", index=False)
        else:
            folder = source / group
            folder.mkdir()
            for station, rows in frame.groupby("station_id"):
                rows.to_csv(folder / f"{station}_{group}_sample.csv", index=False)
    # Previous rejected rows must disappear even from unselected outputs.
    output.mkdir()
    stale = meta.copy()
    stale["measurement_date"] = "20250711"
    stale["measurement_time"] = "151429"
    stale.to_csv(output / "Gates.csv", index=False)
    config = tmp_path / "main.yaml"
    config.write_text(yaml.safe_dump({"project": {"name": "test"}, "paths": {"raw_data_dir": str(raw), "runs_root": str(tmp_path / "runs"), "database_root": str(tmp_path)}, "ingest": {"nivus": {"enabled": True}}, "normalize": {
        "input_dir": str(raw), "output_dir": str(output),
        "registry_dir": str(ROOT / "configs/normalization"),
        "groups": ["Points"] if points_only else list(frames), "concat_groups": list(frames), "write_policy": "overwrite",
    }}))
    monkeypatch.setattr(runner, "create_run", lambda *args: tmp_path / "run")
    original = {p: p.read_bytes() for p in raw.rglob("*.csv")}
    run = normalize_database(config)
    report = pd.read_csv(run / "outputs/rejected_measurements.csv")
    assert len(report) == 1
    assert report.iloc[0].velocity_raw == "#-1"
    for path in output.rglob("*.csv"):
        frame = pd.read_csv(path, dtype=str)
        assert set(frame.station_id) == {"GOOD"}, path
    assert len(pd.read_csv(output / "Points.csv")) == 2
    assert all(path.read_bytes() == content for path, content in original.items())


def test_other_qc_errors_still_fail():
    registry = NormalizationRegistry(ROOT / "configs/normalization")
    frame = points("0.5")
    frame["pos [m]"] = -1
    with pytest.raises(ValueError):
        normalize_table(frame, registry.get("nivus", "Points"))


def test_incomplete_identity_fails_closed():
    with pytest.raises(ValueError, match="identity is incomplete"):
        measurement_keys(pd.DataFrame({"station_id": ["bad"]}))


@pytest.mark.parametrize("layout", ["concat", "files"])
def test_all_rejected_points_need_no_sections_and_leave_no_outputs(tmp_path, layout):
    from aforix.normalize.run import _normalize_concat_group, _normalize_file_group
    raw = tmp_path / "raw"
    source = raw / "nivus"
    source.mkdir(parents=True)
    if layout == "concat":
        path = source / "Points.csv"
    else:
        folder = source / "Points"
        folder.mkdir()
        path = folder / "bad_Points_sample.csv"
    points("#-1").to_csv(path, index=False)
    registry = NormalizationRegistry(ROOT / "configs/normalization")
    rejected, _ = find_rejections(raw, ["nivus"], registry)
    registry.excluded_measurements = rejected
    output = tmp_path / "normalized"
    kwargs = dict(instrument="nivus", group="Points", output_root=output,
                  registry=registry, write_policy="overwrite")
    if layout == "concat":
        assert _normalize_concat_group(path, **kwargs) is None
    else:
        assert _normalize_file_group(path.parent, **kwargs) == []
    assert list(output.rglob("*.csv")) == []


def test_rejection_cleanup_only_removes_matching_measurements(tmp_path):
    from aforix.normalize.rejections import purge_rejected_outputs
    path = tmp_path / "Summary.csv"
    original = points("0.5", "GOOD")
    original.to_csv(path, index=False)
    before = path.read_bytes()
    purge_rejected_outputs(tmp_path, {("nivus", "BAD", "20250711", "151429")})
    assert path.read_bytes() == before
