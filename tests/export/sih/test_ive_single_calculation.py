from types import SimpleNamespace

import pandas as pd

from aforix.export.sih import ive_integration


def test_prepared_ive_is_reused_by_excel(monkeypatch, tmp_path):
    calls = []
    captured = {}

    df = pd.DataFrame({
        "distance_m": [0.0, 1.0],
        "depth_m": [0.0, 0.5],
        "velocity_mean_m_s": [0.0, 0.3],
        "width_m": [1.0, 1.0],
    })

    result = SimpleNamespace(
        status="provisional",
        quality="Buena",
        relative_uncertainty_pct=5.25,
        absolute_uncertainty_m3s=0.0021,
    )

    def fake_calculation(*args, **kwargs):
        calls.append(1)
        return df, result

    def fake_excel(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return tmp_path / "ive.xlsx"

    monkeypatch.setattr(
        ive_integration,
        "_calculate_sih_ive",
        fake_calculation,
    )
    monkeypatch.setattr(
        ive_integration,
        "write_ive_excel_report",
        fake_excel,
    )

    measurement = pd.Series({
        "station_id": "7003",
        "measurement_date": "2026-01-22",
        "measurement_time": "11:16:00",
    })

    prepared = ive_integration.prepare_sih_ive(
        tmp_path, "flowtracker", measurement
    )

    fields = ive_integration._sih_fields_from_ive_result(prepared[1])

    ive_integration.write_sih_ive_report(
        tmp_path,
        tmp_path,
        "flowtracker",
        measurement,
        prepared=prepared,
    )

    assert len(calls) == 1
    assert prepared[0] is df
    assert prepared[1] is result
    assert fields["incertidumbre_IVE"] == 5.25
    assert fields["error_IVE"] == 0.0021
    assert fields["calidad_IVE"] == "Buena"
    assert captured
