from datetime import datetime

import pandas as pd

from aforix.ingest import m9


def test_m9_ingest_handles_empty_mat_directory(tmp_path, monkeypatch, capsys):
    config_path = tmp_path / "main.yaml"
    config_path.write_text("test", encoding="utf-8")
    run_dir = tmp_path / "run"
    raw_root = tmp_path / "raw"
    raw_root.mkdir()

    monkeypatch.setattr(
        m9,
        "load_config",
        lambda _: {"ingest": {"m9": {"enabled": True}}, "project": {"timezone": "UTC"}},
    )
    monkeypatch.setattr(m9, "create_run", lambda *_: run_dir)
    monkeypatch.setattr(m9, "_get_m9_raw_root", lambda *_, **__: raw_root)
    monkeypatch.setattr(m9, "find_files_recursive", lambda *_: [])

    result = m9.run(config_path)

    assert result == run_dir
    assert (run_dir / "outputs" / "raw_canonical" / "m9" / "Summary").is_dir()
    assert (run_dir / "outputs" / "raw_canonical" / "m9" / "Points").is_dir()
    assert "Found RiverSurveyor Live MAT files: 0" in capsys.readouterr().out


def test_m9_ingest_preserves_same_station_timestamp_sources(tmp_path, monkeypatch):
    config_path = tmp_path / "main.yaml"
    config_path.write_text("test", encoding="utf-8")
    run_dir = tmp_path / "run"
    raw_root = tmp_path / "raw"
    raw_root.mkdir()
    sources = [raw_root / "transect.mat", raw_root / "transectr.mat"]

    monkeypatch.setattr(
        m9,
        "load_config",
        lambda _: {"ingest": {"m9": {"enabled": True}}, "project": {"timezone": "UTC"}},
    )
    monkeypatch.setattr(m9, "create_run", lambda *_: run_dir)
    monkeypatch.setattr(m9, "_get_m9_raw_root", lambda *_, **__: raw_root)
    monkeypatch.setattr(m9, "find_files_recursive", lambda *_: sources)
    monkeypatch.setattr(m9, "fallback_station_id_from_parents", lambda _: "7071")
    monkeypatch.setattr(
        m9,
        "parse_m9_mat",
        lambda *_args, **_kwargs: {
            "summary": {
                "measurement_start": datetime(2026, 1, 20, 14, 15, 19),
                "measurement_end": datetime(2026, 1, 20, 14, 16, 0),
                "station_id": "7071",
                "station_name": "Test",
                "width_total_m": 12.0,
            },
            "points": [{"sample_number": 1, "width_m": None}],
        },
    )

    m9.run(config_path)

    output_root = run_dir / "outputs" / "raw_canonical" / "m9"
    summary_files = list((output_root / "Summary").glob("*.csv"))
    points_files = list((output_root / "Points").glob("*.csv"))
    assert len(summary_files) == 2
    assert len(points_files) == 2
    assert {path.name for path in summary_files}.isdisjoint(
        {path.name for path in points_files}
    )
    assert {pd.read_csv(path).loc[0, "input_file"] for path in summary_files} == {
        "transect.mat",
        "transectr.mat",
    }


def test_m9_ingest_failure_is_not_reported_as_success(tmp_path, monkeypatch):
    import json
    import pytest
    raw = tmp_path / 'raw'
    raw.mkdir()
    (raw / 'broken.mat').write_bytes(b'broken')
    run_dir = tmp_path / 'run'
    monkeypatch.setattr(m9, 'load_config', lambda _: {'ingest': {'m9': {'enabled': True}}})
    monkeypatch.setattr(m9, 'create_run', lambda *_: run_dir)
    monkeypatch.setattr(m9, '_get_m9_raw_root', lambda *_, **__: raw)
    with pytest.raises(RuntimeError, match='ingestion incomplete'):
        m9.run(tmp_path / 'main.yaml')
    status = json.loads((run_dir / 'ingest_status.json').read_text())
    assert status['succeeded'] == 0
    assert len(status['failed']) == 1
