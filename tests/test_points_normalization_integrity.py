from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml

from aforix.ingest.adapters.flowtracker_dis import parse_flowtracker_dis
from aforix.normalize.normalizer import normalize_table
from aforix.normalize.run import (
    _enrich_points_with_summary_width,
    _enrich_written_points_width,
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
        output_root=output_root,
        instrument=instrument,
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
        output_root=output_root,
        instrument=instrument,
    )
    _write_cross_instrument_concat(
        enriched_frames,
        group="Points",
        output_root=output_root,
        write_policy="overwrite",
    )

    global_points = pd.read_csv(output_root / "Points.csv")
    assert global_points["width_m"].tolist() == pytest.approx([14.7, 14.7])

