from datetime import datetime

import pandas as pd

from aforix.export.sih.mappings import build_sdh_aforos_row


def test_sih_aforo_uses_configured_end_datetime_when_present():
    measurement = pd.Series(
        {
            "measurement_end_date": "20260703",
            "measurement_end_time": "113241",
            "width_total_m": 31.3,
            "q_total_m3s": 5.0,
            "depth_mean_m": 0.9,
            "area_total_m2": 32.0,
            "velocity_mean_m_s": 0.15625,
            "hydraulic_radius_m": 1.28,
        }
    )
    instrument_cfg = {
        "normalized_fields": {
            "ancho": "width_total_m",
            "caudal": "q_total_m3s",
            "profundidad": "depth_mean_m",
            "seccion": "area_total_m2",
            "velocidad_media": "velocity_mean_m_s",
            "radio_hidraulico": "hydraulic_radius_m",
            "fecha_fin_date": "measurement_end_date",
            "fecha_fin_time": "measurement_end_time",
        }
    }

    row = build_sdh_aforos_row(
        measurement,
        instrument_cfg,
        datetime(2026, 7, 3, 11, 30, 24),
        "%d/%m/%Y %H:%M:%S",
        id_estacion="133",
        id_instrumento="503",
        id_tipo_aforo="59",
        id_instrumentos_rangos="12",
    )

    assert row["fecha_inicio"] == "03/07/2026 11:30:24"
    assert row["fecha_fin"] == "03/07/2026 11:32:41"
    assert row["radio_hidraulico"] == "1.28"
