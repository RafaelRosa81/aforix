from types import SimpleNamespace
"""Integration tests for SIH export metadata."""

from pathlib import Path

import pandas as pd

from aforix.export.sih.runner import (
    SihExportRequest,
    run_sih_export,
)


def test_runner_records_unresolved_measurement(tmp_path, monkeypatch):
    from aforix.export.sih import runner

    output_dir = tmp_path / "output"
    normalized_root = tmp_path / "normalized"
    normalized_root.mkdir()

    selection = tmp_path / "selection.csv"
    pd.DataFrame([{
        "instrument": "flowtracker",
        "station_id": "7003",
        "measurement_date": "2026-01-22",
        "measurement_time": "11:16:00",
        "export_id": "TEST",
    }]).to_csv(selection, index=False)

    summary_dir = normalized_root / "flowtracker"
    summary_dir.mkdir()

    pd.DataFrame([{
        "instrument": "flowtracker",
        "station_id": "9999",
        "measurement_date": "2026-01-22",
        "measurement_time": "11:16:00",
    }]).to_csv(summary_dir / "Summary.csv", index=False)

    config = {
        "sih": {
            "output": {"output_dir": str(output_dir)},
            "instruments": {"flowtracker": {}},
        }
    }

    monkeypatch.setattr(
        runner, "load_sih_config", lambda path: config
    )
    monkeypatch.setattr(
        runner, "get_normalized_input_dir",
        lambda config: normalized_root
    )
    monkeypatch.setattr(
        runner, "get_raw_canonical_input_dir",
        lambda config: tmp_path / "raw"
    )
    monkeypatch.setattr(
        runner, "get_output_dir",
        lambda config: output_dir
    )
    monkeypatch.setattr(
        runner, "get_lookup_file_paths",
        lambda config: {}
    )

    result = run_sih_export(
        SihExportRequest(
            sih_config_path=tmp_path / "unused.yaml",
            selection_file=selection,
        )
    )

    metadata_path = output_dir / "sih_export_metadata.csv"

    assert metadata_path.exists()
    assert metadata_path in result.exported_files

    metadata = pd.read_csv(metadata_path)

    assert len(metadata) == 1
    assert metadata.loc[0, "status"] == "error"
    assert metadata.loc[0, "export_id"] == "TEST"
    assert metadata.loc[0, "instrument"] == "flowtracker"
    assert "No measurement found" in metadata.loc[0, "error"]



def test_runner_success_preserves_sih_ive_fields(tmp_path, monkeypatch):
    from aforix.export.sih import runner

    output_dir = tmp_path / "output"
    selection = tmp_path / "selection.csv"

    pd.DataFrame([{
        "instrument": "flowtracker",
        "station_id": "7003",
        "measurement_date": "2026-01-22",
        "measurement_time": "11:16:00",
        "export_id": "TEST",
    }]).to_csv(selection, index=False)

    measurement = pd.Series({
        "station_id": "7003",
        "measurement_date": "2026-01-22",
        "measurement_time": "11:16:00",
    })

    config = {
        "sih": {
            "output": {"output_dir": str(output_dir)},
            "instruments": {"flowtracker": {}},
        }
    }

    monkeypatch.setattr(runner, "load_sih_config", lambda path: config)
    monkeypatch.setattr(runner, "get_normalized_input_dir", lambda config: tmp_path)
    monkeypatch.setattr(runner, "get_raw_canonical_input_dir", lambda config: tmp_path)
    monkeypatch.setattr(runner, "get_output_dir", lambda config: output_dir)
    monkeypatch.setattr(runner, "get_lookup_file_paths", lambda config: {})
    monkeypatch.setattr(runner, "load_lookup_tables", lambda paths: {})
    monkeypatch.setattr(runner, "load_normalized_summary", lambda *args: pd.DataFrame([measurement]))
    monkeypatch.setattr(runner, "load_raw_canonical_summary", lambda *args: None)
    monkeypatch.setattr(runner, "resolve_measurement", lambda *args: measurement)
    monkeypatch.setattr(runner, "resolve_optional_measurement", lambda *args: None)

    monkeypatch.setattr(runner, "resolve_station_id", lambda *args: "7003")
    monkeypatch.setattr(runner, "resolve_instrument_lookup_id", lambda *args: "1")
    monkeypatch.setattr(runner, "resolve_tipo_aforo_lookup_id", lambda *args: "2")
    monkeypatch.setattr(runner, "resolve_instrumentos_rangos_lookup_id", lambda *args: "3")

    monkeypatch.setattr(
        runner,
        "build_sdh_actuaciones_row",
        lambda *args, **kwargs: {"id_estacion": "7003"},
    )
    monkeypatch.setattr(
        runner,
        "build_sdh_aforos_row",
        lambda *args, **kwargs: {"id_estacion": "7003"},
    )

    expected_ive = {
        "incertidumbre_IVE": 5.25,
        "error_IVE": 0.0021,
        "calidad_IVE": "Buena",
    }

    monkeypatch.setattr(
        runner,
        "prepare_sih_ive",
        lambda *args, **kwargs: (
            pd.DataFrame(),
            SimpleNamespace(
                relative_uncertainty_pct=5.25,
                absolute_uncertainty_m3s=0.0021,
                quality="Buena",
                status="provisional",
            ),
        ),
    )

    def fake_report(normalized_root, report_root, instrument, measurement, parameters=None, prepared=None):
        report_root = Path(report_root)
        report_root.mkdir(parents=True, exist_ok=True)
        report_path = report_root / "test_ive.xlsx"
        report_path.touch()
        return report_path

    monkeypatch.setattr(runner, "write_sih_ive_report", fake_report)

    result = runner.run_sih_export(
        SihExportRequest(
            sih_config_path=tmp_path / "unused.yaml",
            selection_file=selection,
        )
    )

    metadata = pd.read_csv(output_dir / "sih_export_metadata.csv")

    assert len(metadata) == 1
    assert metadata.loc[0, "status"] == "success", metadata.loc[0, "error"]
    assert metadata.loc[0, "ive_report_error"] != metadata.loc[0, "ive_report_error"] or (
        metadata.loc[0, "ive_report_error"] == ""
    )

    aforos_files = [
        path for path in result.exported_files
        if "_aforo_" in path.name and path.suffix == ".csv"
    ]

    assert len(aforos_files) == 1

    aforos = pd.read_csv(aforos_files[0])

    assert aforos.loc[0, "incertidumbre_IVE"] == 5.25
    assert aforos.loc[0, "error_IVE"] == 0.0021
    assert aforos.loc[0, "calidad_IVE"] == "Buena"

    assert Path(metadata.loc[0, "ive_report_file"]).exists()



def test_runner_records_ive_calculated_metadata(tmp_path, monkeypatch):
    """IVE methodological status is separate from SIH export status."""
    from aforix.export.sih import runner

    output_dir = tmp_path / "output"
    selection = tmp_path / "selection.csv"

    pd.DataFrame([{
        "instrument": "flowtracker",
        "station_id": "7003",
        "measurement_date": "2026-01-22",
        "measurement_time": "11:16:00",
        "export_id": "TEST",
    }]).to_csv(selection, index=False)

    measurement = pd.Series({
        "station_id": "7003",
        "measurement_date": "2026-01-22",
        "measurement_time": "11:16:00",
    })

    config = {
        "sih": {
            "output": {"output_dir": str(output_dir)},
            "instruments": {"flowtracker": {}},
        }
    }

    monkeypatch.setattr(runner, "load_sih_config", lambda path: config)
    monkeypatch.setattr(runner, "get_normalized_input_dir", lambda config: tmp_path)
    monkeypatch.setattr(runner, "get_raw_canonical_input_dir", lambda config: tmp_path)
    monkeypatch.setattr(runner, "get_output_dir", lambda config: output_dir)
    monkeypatch.setattr(runner, "get_lookup_file_paths", lambda config: {})
    monkeypatch.setattr(runner, "load_lookup_tables", lambda paths: {})
    monkeypatch.setattr(runner, "load_normalized_summary", lambda *args: pd.DataFrame([measurement]))
    monkeypatch.setattr(runner, "load_raw_canonical_summary", lambda *args: None)
    monkeypatch.setattr(runner, "resolve_measurement", lambda *args: measurement)
    monkeypatch.setattr(runner, "resolve_optional_measurement", lambda *args: None)

    monkeypatch.setattr(runner, "resolve_station_id", lambda *args: "7003")
    monkeypatch.setattr(runner, "resolve_instrument_lookup_id", lambda *args: "1")
    monkeypatch.setattr(runner, "resolve_tipo_aforo_lookup_id", lambda *args: "2")
    monkeypatch.setattr(runner, "resolve_instrumentos_rangos_lookup_id", lambda *args: "3")

    monkeypatch.setattr(
        runner, "build_sdh_actuaciones_row",
        lambda *args, **kwargs: {"id_estacion": "7003"},
    )
    monkeypatch.setattr(
        runner, "build_sdh_aforos_row",
        lambda *args, **kwargs: {"id_estacion": "7003"},
    )

    monkeypatch.setattr(
        runner,
        "prepare_sih_ive",
        lambda *args, **kwargs: (
            pd.DataFrame(),
            SimpleNamespace(
                relative_uncertainty_pct=5.25,
                absolute_uncertainty_m3s=0.0021,
                quality="Buena",
                status="calculated",
            ),
        ),
    )

    def fake_report(normalized_root, report_root, instrument, measurement, parameters=None, prepared=None):
        report_root = Path(report_root)
        report_root.mkdir(parents=True, exist_ok=True)
        report_path = report_root / "test_ive.xlsx"
        report_path.touch()
        return report_path

    monkeypatch.setattr(runner, "write_sih_ive_report", fake_report)

    original_prepare = runner.prepare_sih_ive
    original_report = runner.write_sih_ive_report
    prepared_calls = []
    report_calls = []

    def counted_prepare(*args, **kwargs):
        result = original_prepare(*args, **kwargs)
        prepared_calls.append(result)
        return result

    def checked_report(*args, **kwargs):
        report_calls.append(kwargs.get("prepared"))
        return original_report(*args, **kwargs)

    monkeypatch.setattr(runner, "prepare_sih_ive", counted_prepare)
    monkeypatch.setattr(runner, "write_sih_ive_report", checked_report)

    runner.run_sih_export(
        SihExportRequest(
            sih_config_path=tmp_path / "unused.yaml",
            selection_file=selection,
        )
    )

    metadata = pd.read_csv(output_dir / "sih_export_metadata.csv")

    assert metadata.loc[0, "status"] == "success"
    assert len(prepared_calls) == 1
    assert len(report_calls) == 1
    assert report_calls[0] is prepared_calls[0]
    assert metadata.loc[0, "ive_status"] == "calculated"
    assert metadata.loc[0, "ive_reason"] == (
        "Metodo IVE: se utiliza s_v,IVE; no se aplica s_v,min."
    )
    assert metadata.loc[0, "ive_reason"].strip()
    assert Path(metadata.loc[0, "ive_report_file"]).exists()
