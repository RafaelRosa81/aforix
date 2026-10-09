from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml

from aforix.ingest.adapters.flowtracker_dis import parse_flowtracker_dis
from aforix.normalize.normalizer import normalize_table
import aforix.normalize.run as normalize_run_module
from aforix.normalize.run import (
    _clear_stale_concat_outputs,
    _enrich_points_with_summary_width,
    _enrich_written_points_width,
    _enrich_nivus_points_from_sections,
    _normalize_concat_group,
    _normalize_file_group,
    _normalize_nivus_points_with_sections,
    _prepare_group_output_layout,
    normalize_database,
    _raise_width_enrichment_failure,
    _write_cross_instrument_concat,
)


ROOT = Path(__file__).resolve().parents[1]


def _load_points_spec(instrument: str) -> dict:
    path = ROOT / "configs" / "normalization" / f"{instrument}.yaml"
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)["tables"]["Points"]


def _add_measurement_metadata(df: pd.DataFrame, instrument: str) -> pd.DataFrame:
    out = df.copy()
    out["station_id"] = "7071"
    out["station_name"] = "Test"
    out["measurement_date"] = "20260120"
    out["measurement_time"] = "141519"
    out["instrument"] = instrument
    out["source_file"] = "fixture"
    out["source_run_dir"] = "run"
    out["run_id"] = "run"
    return out


def test_flowtracker_real_vmedia_header_reaches_mean_velocity(tmp_path):
    path = tmp_path / "sample.dis"
    path.write_text(
        "Ancho_total                      14.700 m\n"
        "St Reloj PtoAfo Calado V Vmedia Area Caudal %Q\n"
        "( )\n"
        "1 14:15 0.7 0.16 0.0123 0.0134 0.112 0.0023 1.0\n",
        encoding="utf-8",
    )

    _, raw_points = parse_flowtracker_dis(path)

    assert raw_points.loc[0, "velocity_m_s"] == "0.0123"
    assert raw_points.loc[0, "mean_velocity_m_s"] == "0.0134"
    assert raw_points.loc[0, "percent_discharge"] == "1.0"

    normalized = normalize_table(
        _add_measurement_metadata(raw_points, "flowtracker"),
        _load_points_spec("flowtracker"),
    )

    assert normalized.loc[0, "velocity_mean_m_s"] == pytest.approx(0.0134)
    assert normalized.loc[0, "percent_q"] == pytest.approx(1.0)


def test_molinete_points_preserve_label_velocity_and_percent_q():
    raw = _add_measurement_metadata(
        pd.DataFrame(
            [
                {
                    "point_index": "3",
                    "vert_label": "3",
                    "progr_m": "1.4",
                    "prof_m": "0.25",
                    "area_m2": "0.1925",
                    "vel_media_vert_ms": "0.027995",
                    "q_m3s": "0.005389358",
                    "q_percent": "2.576",
                }
            ]
        ),
        "molinete",
    )

    normalized = normalize_table(raw, _load_points_spec("molinete"))

    assert normalized.loc[0, "point_label"] == "3"
    assert normalized.loc[0, "velocity_mean_m_s"] == pytest.approx(0.027995)
    assert normalized.loc[0, "percent_q"] == pytest.approx(2.576)


def test_nivus_quality_percentages_do_not_masquerade_as_percent_q():
    raw = _add_measurement_metadata(
        pd.DataFrame(
            [
                {
                    "index": "1",
                    "pos [m]": "0.2",
                    "h [m]": "0.1862",
                    "v [m/s]": "0.0463",
                    "tq [%]": "6.67",
                    "atq [%]": "25.0",
                    "hq [%]": "100.0",
                    "t [°C]": "25.19",
                    "h_meas [m]": "0.1862",
                    "mtime [s]": "30",
                }
            ]
        ),
        "nivus",
    )

    normalized = normalize_table(raw, _load_points_spec("nivus"))

    assert pd.isna(normalized.loc[0, "percent_q"])


@pytest.mark.parametrize(
    ("instrument", "width"),
    [
        ("flowtracker", 14.7),
        ("molinete", 14.825),
        ("nivus", 4.0),
    ],
)
def test_points_width_is_repeated_from_summary_for_every_instrument(instrument, width):
    points = pd.DataFrame(
        [
            {
                "instrument": instrument,
                "station_id": "7071",
                "measurement_date": "20260120",
                "measurement_time": "141519",
                "width_m": pd.NA,
                "point_index": 1,
            },
            {
                "instrument": instrument,
                "station_id": "7071",
                "measurement_date": "20260120",
                "measurement_time": "141519",
                "width_m": pd.NA,
                "point_index": 2,
            },
        ]
    )
    summary = pd.DataFrame(
        [
            {
                "instrument": instrument,
                "station_id": "7071",
                "measurement_date": "20260120",
                "measurement_time": "141519",
                "width_total_m": width,
            }
        ]
    )

    enriched = _enrich_points_with_summary_width(
        points,
        summary,
        label=f"{instrument}/fixture",
    )

    assert enriched["width_m"].tolist() == pytest.approx([width, width])


def test_points_width_rejects_conflicting_summary_values():
    points = pd.DataFrame(
        [
            {
                "instrument": "flowtracker",
                "station_id": "7071",
                "measurement_date": "20260120",
                "measurement_time": "141519",
                "width_m": pd.NA,
            }
        ]
    )
    summary = pd.DataFrame(
        [
            {
                "instrument": "flowtracker",
                "station_id": "7071",
                "measurement_date": "20260120",
                "measurement_time": "141519",
                "width_total_m": 14.7,
            },
            {
                "instrument": "flowtracker",
                "station_id": "7071",
                "measurement_date": "20260120",
                "measurement_time": "141519",
                "width_total_m": 14.8,
            },
        ]
    )

    with pytest.raises(ValueError, match="Conflicting Summary.width_total_m"):
        _enrich_points_with_summary_width(
            points,
            summary,
            label="flowtracker/fixture",
        )


def test_written_width_enrichment_supports_summary_file_group(tmp_path):
    output_root = tmp_path / "normalized"
    instrument = "molinete"

    summary_dir = output_root / instrument / "Summary"
    points_dir = output_root / instrument / "Points"
    summary_dir.mkdir(parents=True)
    points_dir.mkdir(parents=True)

    pd.DataFrame(
        [
            {
                "instrument": instrument,
                "station_id": "7071",
                "measurement_date": "20260120",
                "measurement_time": "141519",
                "width_total_m": 14.825,
            }
        ]
    ).to_csv(summary_dir / "7071_Summary.csv", index=False)

    pd.DataFrame(
        [
            {
                "instrument": instrument,
                "station_id": "7071",
                "measurement_date": "20260120",
                "measurement_time": "141519",
                "point_index": 1,
                "width_m": pd.NA,
            },
            {
                "instrument": instrument,
                "station_id": "7071",
                "measurement_date": "20260120",
                "measurement_time": "141519",
                "point_index": 2,
                "width_m": pd.NA,
            },
        ]
    ).to_csv(points_dir / "7071_Points.csv", index=False)

    frames = _enrich_written_points_width(
        instrument=instrument,
        summary_paths=[summary_dir / "7071_Summary.csv"],
        point_paths=[points_dir / "7071_Points.csv"],
    )

    written = pd.read_csv(points_dir / "7071_Points.csv")
    assert written["width_m"].tolist() == pytest.approx([14.825, 14.825])
    assert len(frames) == 1
    assert frames[0]["width_m"].tolist() == pytest.approx([14.825, 14.825])


def test_cross_instrument_points_concat_uses_enriched_frames(tmp_path):
    output_root = tmp_path / "normalized"
    instrument = "flowtracker"

    instrument_dir = output_root / instrument
    instrument_dir.mkdir(parents=True)

    pd.DataFrame(
        [
            {
                "instrument": instrument,
                "station_id": "7071",
                "measurement_date": "20260120",
                "measurement_time": "141519",
                "width_total_m": 14.7,
            }
        ]
    ).to_csv(instrument_dir / "Summary.csv", index=False)

    pd.DataFrame(
        [
            {
                "instrument": instrument,
                "station_id": "7071",
                "measurement_date": "20260120",
                "measurement_time": "141519",
                "point_index": 1,
                "width_m": pd.NA,
            },
            {
                "instrument": instrument,
                "station_id": "7071",
                "measurement_date": "20260120",
                "measurement_time": "141519",
                "point_index": 2,
                "width_m": pd.NA,
            },
        ]
    ).to_csv(instrument_dir / "Points.csv", index=False)

    enriched_frames = _enrich_written_points_width(
        instrument=instrument,
        summary_paths=[instrument_dir / "Summary.csv"],
        point_paths=[instrument_dir / "Points.csv"],
    )
    _write_cross_instrument_concat(
        enriched_frames,
        group="Points",
        output_root=output_root,
        write_policy="overwrite",
    )

    global_points = pd.read_csv(output_root / "Points.csv")
    assert global_points["width_m"].tolist() == pytest.approx([14.7, 14.7])


def test_nivus_concat_points_are_enriched_from_concat_sections(tmp_path, monkeypatch):
    input_dir = tmp_path / "raw_canonical" / "nivus"
    output_root = tmp_path / "normalized"
    input_dir.mkdir(parents=True)

    points_path = input_dir / "Points.csv"
    sections_path = input_dir / "Sections.csv"
    points_path.write_text("placeholder\n", encoding="utf-8")
    sections_path.write_text("placeholder\n", encoding="utf-8")

    points = pd.DataFrame(
        [
            {
                "instrument": "nivus",
                "station_id": "7001",
                "measurement_date": "20260120",
                "measurement_time": "141519",
                "point_index": 1,
                "area_m2": pd.NA,
                "q_ls": pd.NA,
                "q_m3s": pd.NA,
                "percent_q": pd.NA,
            },
            {
                "instrument": "nivus",
                "station_id": "7001",
                "measurement_date": "20260120",
                "measurement_time": "141519",
                "point_index": 2,
                "area_m2": pd.NA,
                "q_ls": pd.NA,
                "q_m3s": pd.NA,
                "percent_q": pd.NA,
            },
        ]
    )
    sections = pd.DataFrame(
        [
            {
                "instrument": "nivus",
                "station_id": "7001",
                "measurement_date": "20260120",
                "measurement_time": "141519",
                "section_index": 1,
                "width_m": 0.5,
                "depth_m": 0.2,
                "q_ls": 10.0,
                "percent_q": 10.0,
            },
            {
                "instrument": "nivus",
                "station_id": "7001",
                "measurement_date": "20260120",
                "measurement_time": "141519",
                "section_index": 2,
                "width_m": 0.5,
                "depth_m": 0.2,
                "q_ls": 20.0,
                "percent_q": 20.0,
            },
            {
                "instrument": "nivus",
                "station_id": "7001",
                "measurement_date": "20260120",
                "measurement_time": "141519",
                "section_index": 3,
                "width_m": 0.5,
                "depth_m": 0.2,
                "q_ls": 30.0,
                "percent_q": 30.0,
            },
            {
                "instrument": "nivus",
                "station_id": "7001",
                "measurement_date": "20260120",
                "measurement_time": "141519",
                "section_index": 4,
                "width_m": 0.5,
                "depth_m": 0.2,
                "q_ls": 40.0,
                "percent_q": 40.0,
            },
        ]
    )

    def fake_normalize(path, *, instrument, group, registry):
        return points.copy() if group == "Points" else sections.copy()

    monkeypatch.setattr(normalize_run_module, "_normalize_single_csv", fake_normalize)

    result = _normalize_concat_group(
        points_path,
        instrument="nivus",
        group="Points",
        output_root=output_root,
        registry=object(),
        write_policy="overwrite",
    )

    assert result is not None
    assert result["percent_q"].tolist() == pytest.approx([30.0, 70.0])
    assert result["q_ls"].tolist() == pytest.approx([30.0, 70.0])
    assert result["q_m3s"].tolist() == pytest.approx([0.03, 0.07])


def test_width_enrichment_uses_only_current_run_point_paths(tmp_path):
    output_root = tmp_path / "normalized"
    instrument = "molinete"
    summary_dir = output_root / instrument / "Summary"
    points_dir = output_root / instrument / "Points"
    summary_dir.mkdir(parents=True)
    points_dir.mkdir(parents=True)

    current_summary = summary_dir / "current_Summary.csv"
    current_points = points_dir / "current_Points.csv"
    stale_points = points_dir / "stale_Points.csv"

    pd.DataFrame(
        [
            {
                "instrument": instrument,
                "station_id": "7071",
                "measurement_date": "20260120",
                "measurement_time": "141519",
                "width_total_m": 14.8,
            }
        ]
    ).to_csv(current_summary, index=False)

    pd.DataFrame(
        [
            {
                "instrument": instrument,
                "station_id": "7071",
                "measurement_date": "20260120",
                "measurement_time": "141519",
                "point_index": 1,
                "width_m": pd.NA,
            }
        ]
    ).to_csv(current_points, index=False)

    pd.DataFrame(
        [
            {
                "instrument": instrument,
                "station_id": "9999",
                "measurement_date": "20250101",
                "measurement_time": "000000",
                "point_index": 1,
                "width_m": 99.0,
            }
        ]
    ).to_csv(stale_points, index=False)

    frames = _enrich_written_points_width(
        instrument=instrument,
        summary_paths=[current_summary],
        point_paths=[current_points],
    )

    assert len(frames) == 1
    assert frames[0]["station_id"].tolist() == ["7071"]
    assert frames[0]["width_m"].tolist() == pytest.approx([14.8])

    stale = pd.read_csv(stale_points, dtype={"station_id": "string"})
    assert stale["station_id"].tolist() == ["9999"]


def test_width_enrichment_failure_removes_invalid_points_and_propagates(tmp_path):
    output_root = tmp_path / "normalized"
    instrument_dir = output_root / "flowtracker"
    instrument_dir.mkdir(parents=True)

    point_path = instrument_dir / "Points.csv"
    global_points = output_root / "Points.csv"
    point_path.write_text("bad\n", encoding="utf-8")
    global_points.write_text("stale\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Failed enriching flowtracker/Points.width_m"):
        _raise_width_enrichment_failure(
            instrument="flowtracker",
            point_paths=[point_path],
            output_root=output_root,
            exc=ValueError("missing width"),
        )

    assert not point_path.exists()
    assert not global_points.exists()


def test_overwrite_rebuild_clears_prior_root_concat_outputs(tmp_path):
    output_root = tmp_path / "normalized"
    output_root.mkdir()
    (output_root / "Points.csv").write_text("stale\n", encoding="utf-8")
    (output_root / "Summary.csv").write_text("stale\n", encoding="utf-8")
    (output_root / "Other.csv").write_text("keep\n", encoding="utf-8")

    _clear_stale_concat_outputs(
        output_root=output_root,
        concat_groups={"Points", "Summary"},
    )

    assert not (output_root / "Points.csv").exists()
    assert not (output_root / "Summary.csv").exists()
    assert (output_root / "Other.csv").exists()


def test_nivus_file_group_points_require_matching_sections(tmp_path, monkeypatch):
    points_dir = tmp_path / "raw_canonical" / "nivus" / "Points"
    points_dir.mkdir(parents=True)
    points_path = points_dir / "7001_Points_20260120_141519.csv"
    points_path.write_text("placeholder\n", encoding="utf-8")

    monkeypatch.setattr(
        normalize_run_module,
        "_normalize_single_csv",
        lambda *args, **kwargs: pd.DataFrame(
            [
                {
                    "instrument": "nivus",
                    "station_id": "7001",
                    "measurement_date": "20260120",
                    "measurement_time": "141519",
                    "point_index": 1,
                    "percent_q": pd.NA,
                }
            ]
        ),
    )

    with pytest.raises(FileNotFoundError, match="Matching Nivus Sections file not found"):
        _normalize_nivus_points_with_sections(
            points_path,
            registry=object(),
        )


def test_file_group_failure_cleans_stale_outputs_and_writes_nothing_partial(
    tmp_path,
    monkeypatch,
):
    input_dir = tmp_path / "raw_canonical" / "flowtracker" / "Points"
    output_root = tmp_path / "normalized"
    output_dir = output_root / "flowtracker" / "Points"
    input_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)

    first = input_dir / "a.csv"
    second = input_dir / "b.csv"
    first.write_text("placeholder\n", encoding="utf-8")
    second.write_text("placeholder\n", encoding="utf-8")
    (output_dir / "stale.csv").write_text("stale\n", encoding="utf-8")

    def fake_normalize(path, *, instrument, group, registry):
        if path.name == "b.csv":
            raise ValueError("second file failed")
        return pd.DataFrame([{"point_index": 1}])

    monkeypatch.setattr(normalize_run_module, "_normalize_single_csv", fake_normalize)

    with pytest.raises(ValueError, match="second file failed"):
        _normalize_file_group(
            input_dir,
            instrument="flowtracker",
            group="Points",
            output_root=output_root,
            registry=object(),
            write_policy="overwrite",
        )

    assert list(output_dir.glob("*.csv")) == []


def test_normalize_database_propagates_collected_group_failures(tmp_path, monkeypatch):
    config_path = tmp_path / "main.yaml"
    config_path.write_text("normalize: {}\n", encoding="utf-8")

    input_root = tmp_path / "raw"
    output_root = tmp_path / "normalized"
    registry_root = tmp_path / "registry"
    (input_root / "flowtracker" / "Points").mkdir(parents=True)
    registry_root.mkdir()

    cfg = {
        "ingest": {"flowtracker": {"enabled": True}},
        "normalize": {
            "enabled": True,
            "sources": ["flowtracker"],
            "groups": ["Points"],
            "concat_groups": ["Points"],
            "write_policy": "overwrite",
            "input_dir": str(input_root),
            "output_dir": str(output_root),
            "registry_dir": str(registry_root),
        },
    }

    class DummyRegistry:
        def get(self, instrument, group):
            return {}

    monkeypatch.setattr(normalize_run_module, "load_config", lambda path: cfg)
    monkeypatch.setattr(
        normalize_run_module,
        "create_run",
        lambda stage, path: tmp_path / "run",
    )
    monkeypatch.setattr(
        normalize_run_module,
        "NormalizationRegistry",
        lambda path: DummyRegistry(),
    )
    monkeypatch.setattr(
        normalize_run_module,
        "_normalize_file_group",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("boom")),
    )

    with pytest.raises(RuntimeError, match="Normalization failed"):
        normalize_database(config_path)


def test_nivus_enrichment_rejects_missing_section_hydraulic_values():
    points = pd.DataFrame(
        [
            {"point_index": 1},
            {"point_index": 2},
        ]
    )
    sections = pd.DataFrame(
        [
            {"section_index": 1, "width_m": 0.5, "depth_m": 0.2, "q_ls": 10.0, "percent_q": pd.NA},
            {"section_index": 2, "width_m": 0.5, "depth_m": 0.2, "q_ls": 20.0, "percent_q": 20.0},
            {"section_index": 3, "width_m": 0.5, "depth_m": 0.2, "q_ls": 30.0, "percent_q": 30.0},
            {"section_index": 4, "width_m": 0.5, "depth_m": 0.2, "q_ls": 40.0, "percent_q": 50.0},
        ]
    )

    with pytest.raises(ValueError, match="missing hydraulic values"):
        _enrich_nivus_points_from_sections(
            points,
            sections,
            label="fixture",
        )


def test_file_group_overwrite_removes_stale_concat_layout(tmp_path):
    output_root = tmp_path / "normalized"
    instrument_dir = output_root / "flowtracker"
    group_dir = instrument_dir / "Points"
    instrument_dir.mkdir(parents=True)
    group_dir.mkdir()

    stale_concat = instrument_dir / "Points.csv"
    stale_concat.write_text("stale\n", encoding="utf-8")
    (group_dir / "old.csv").write_text("old\n", encoding="utf-8")

    _prepare_group_output_layout(
        output_root=output_root,
        instrument="flowtracker",
        group="Points",
        layout="file_group",
        write_policy="overwrite",
    )

    assert not stale_concat.exists()
    assert list(group_dir.glob("*.csv")) == []


def test_concat_overwrite_removes_stale_file_group_layout(tmp_path):
    output_root = tmp_path / "normalized"
    instrument_dir = output_root / "flowtracker"
    group_dir = instrument_dir / "Points"
    group_dir.mkdir(parents=True)

    stale_group_file = group_dir / "old.csv"
    stale_group_file.write_text("old\n", encoding="utf-8")

    _prepare_group_output_layout(
        output_root=output_root,
        instrument="flowtracker",
        group="Points",
        layout="concat",
        write_policy="overwrite",
    )

    assert not stale_group_file.exists()
    assert not group_dir.exists()


def test_points_width_requires_non_null_matching_summary_even_if_already_present():
    points = pd.DataFrame(
        [
            {
                "instrument": "flowtracker",
                "station_id": "7071",
                "measurement_date": "20260120",
                "measurement_time": "141519",
                "width_m": 14.7,
            }
        ]
    )
    summary = pd.DataFrame(
        [
            {
                "instrument": "flowtracker",
                "station_id": "9999",
                "measurement_date": "20260120",
                "measurement_time": "141519",
                "width_total_m": 14.7,
            }
        ]
    )

    with pytest.raises(ValueError, match="Missing matching Summary.width_total_m"):
        _enrich_points_with_summary_width(
            points,
            summary,
            label="flowtracker/fixture",
        )

