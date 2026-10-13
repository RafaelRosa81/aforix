from __future__ import annotations

import pandas as pd

from aforix.export.sih.ive_integration import calculate_sih_ive_fields


def _measurement():
    return pd.Series({
        "station_id": "7001",
        "measurement_date": "20260120",
        "measurement_time": "140000",
    })


def _point(x, *, width=3.0):
    return {
        "station_id": "7001",
        "measurement_date": "20260120",
        "measurement_time": "140000",
        "instrument": "flowtracker",
        "distance_m": x,
        "depth_m": 0.0 if x in (0.0, width) else 0.25,
        "velocity_mean_m_s": 0.0 if x in (0.0, width) else 0.35,
        "width_m": width,
    }


def test_ive_export_fields_for_ten_verticals(tmp_path):
    points = [_point(i * 0.25) for i in range(13)]
    pd.DataFrame(points).to_csv(tmp_path / "Points.csv", index=False)
    fields = calculate_sih_ive_fields(tmp_path, "flowtracker", _measurement())
    assert fields["incertidumbre_IVE"] > 0
    assert fields["error_IVE"] > 0
    assert fields["calidad_IVE"] in {"Excelente", "Buena", "Regular", "Mala"}


def test_ive_export_inapplicable_has_blank_numeric_fields(tmp_path):
    points = [_point(i * 0.5) for i in range(7)]
    pd.DataFrame(points).to_csv(tmp_path / "Points.csv", index=False)
    fields = calculate_sih_ive_fields(tmp_path, "flowtracker", _measurement())
    assert fields == {
        "incertidumbre_IVE": "",
        "error_IVE": "",
        "calidad_IVE": "IVE no aplicable: menos de 10 verticales",
    }


def test_ive_export_missing_points_does_not_block_export(tmp_path):
    fields = calculate_sih_ive_fields(tmp_path, "flowtracker", _measurement())
    assert fields["incertidumbre_IVE"] == ""
    assert fields["error_IVE"] == ""
    assert fields["calidad_IVE"].startswith("IVE no disponible:")


def test_ive_export_nivus_uses_normalized_points(tmp_path):
    points = [_point(i * 0.25) for i in range(13)]
    for point in points:
        point["instrument"] = "nivus"
    pd.DataFrame(points).to_csv(tmp_path / "Points.csv", index=False)
    fields = calculate_sih_ive_fields(tmp_path, "nivus", _measurement())
    assert fields["incertidumbre_IVE"] > 0
    assert fields["error_IVE"] > 0
    assert fields["calidad_IVE"] in {"Excelente", "Buena", "Regular", "Mala"}


def test_ive_provisional_result_preserves_sih_values(tmp_path):
    """SIH preserves provisional numeric results without changing quality."""
    from aforix.analysis.uncertainty.calculator import (
        IVEPoint,
        calculate_ive,
    )

    rows = [_point(i * 0.25) for i in range(13)]
    pd.DataFrame(rows).to_csv(tmp_path / "Points.csv", index=False)

    result = calculate_ive(
        [
            IVEPoint(
                distance_m=row["distance_m"],
                depth_m=row["depth_m"],
                velocity_m_s=row["velocity_mean_m_s"],
            )
            for row in rows
        ],
        width_m=3.0,
    )

    fields = calculate_sih_ive_fields(
        tmp_path,
        "flowtracker",
        _measurement(),
    )

    assert result.status == "provisional"
    assert fields["incertidumbre_IVE"] == result.relative_uncertainty_pct
    assert fields["error_IVE"] == result.absolute_uncertainty_m3s
    assert fields["calidad_IVE"] == result.quality
    assert set(fields) == {
        "incertidumbre_IVE",
        "error_IVE",
        "calidad_IVE",
    }
