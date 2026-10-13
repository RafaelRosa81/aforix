from datetime import datetime

import pandas as pd

from aforix.export.sih.mappings import (
    build_sdh_actuaciones_row,
    build_sdh_aforos_row,
)


def test_actuacion_reads_first_operator_token_and_scale_from_normalized_summary():
    config = {
        "id_tipo_actuacion": 4,
        "normalized_fields": {
            "id_operador": "operador",
            "lectura_escala": "escala_inicio",
        },
    }

    for operator, expected in (
        ("Tiago Poren", "Tiago"),
        ("MV__RR", "MV"),
        ("M. Reyes", "M"),
        ("M.Reyes", "M"),
    ):
        measurement = pd.Series({"operador": operator, "escala_inicio": "1.42"})
        row = build_sdh_actuaciones_row(
            measurement,
            config,
            datetime(2026, 1, 22, 11, 50),
            "%d/%m/%Y %H:%M:%S",
            id_estacion="7071",
            id_instrumento="3",
        )

        assert row["id_operador"] == expected
        assert row["lectura_escala"] == "1.42"


def test_aforo_uses_normalized_scales_and_distinct_dates():
    measurement = pd.Series(
        {
            "escala_inicio": "1.42",
            "escala_fin": "1.48",
            "fecha_inicio": "2026-01-22 11:50:00",
            "fecha_fin": "2026-01-22 12:25:00",
        }
    )
    config = {
        "normalized_fields": {
            "escala_inicio": "escala_inicio",
            "escala_fin": "escala_fin",
            "fecha_inicio": "fecha_inicio",
            "fecha_fin": "fecha_fin",
        }
    }

    row = build_sdh_aforos_row(
        measurement,
        config,
        datetime(2026, 1, 22, 11, 50),
        "%d/%m/%Y %H:%M:%S",
        id_estacion="7071",
        id_instrumento="3",
        id_tipo_aforo="4",
        id_instrumentos_rangos="5",
    )

    assert row["escala_inicio"] == "1.42"
    assert row["escala_fin"] == "1.48"
    assert row["fecha_inicio"] == "22/01/2026 11:50:00"
    assert row["fecha_fin"] == "22/01/2026 12:25:00"


def test_missing_flowtracker_metadata_remains_s_d_in_export():
    measurement = pd.Series(
        {
            "escala_inicio": "S/D",
            "escala_fin": "S/D",
            "fecha_inicio": "2026-01-22 11:50:00",
            "fecha_fin": "S/D",
        }
    )
    config = {
        "normalized_fields": {
            "escala_inicio": "escala_inicio",
            "escala_fin": "escala_fin",
            "fecha_inicio": "fecha_inicio",
            "fecha_fin": "fecha_fin",
        }
    }

    row = build_sdh_aforos_row(
        measurement,
        config,
        datetime(2026, 1, 22, 11, 50),
        "%d/%m/%Y %H:%M:%S",
        id_estacion="7001",
        id_instrumento="3",
        id_tipo_aforo="4",
        id_instrumentos_rangos="5",
    )

    assert row["escala_inicio"] == "S/D"
    assert row["escala_fin"] == "S/D"
    assert row["fecha_fin"] == "S/D"
