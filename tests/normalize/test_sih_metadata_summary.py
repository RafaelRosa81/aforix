from pathlib import Path

import pandas as pd
import pytest

from aforix.normalize.normalizer import normalize_table
from aforix.normalize.registry import NormalizationRegistry


REGISTRY = NormalizationRegistry(Path("configs/normalization"))


@pytest.mark.parametrize(
    ("instrument", "row", "expected_end", "expected_start_scale", "expected_end_scale", "expected_operator"),
    [
        (
            "flowtracker",
            {
                "station_id": "7001",
                "measurement_date": "20260122",
                "measurement_time": "115000",
                "instrument": "flowtracker",
                "total_discharge_m3_s": "0.05",
                "scale_start_m": "0.020",
                "scale_end_m": "0.020",
                "complementary_end_datetime": "2023-06-06 11:34:52",
                "operators": "Tiago Poren",
            },
            "2023-06-06 11:34:52",
            "0.020",
            "0.020",
            "Tiago Poren",
        ),
        (
            "molinete",
            {
                "station_id": "7071",
                "measurement_date": "20260122",
                "measurement_time": "115000",
                "instrument": "molinete",
                "q_m3s": "0.05",
                "end_time": "12:25:00",
                "esc_ini_m": "2.11",
                "esc_fin_m": "2.16",
                "realizado": "MV__RR",
            },
            "2026-01-22 12:25:00",
            "2.11",
            "2.16",
            "MV__RR",
        ),
        (
            "nivus",
            {
                "station_id": "7001",
                "measurement_date": "20260122",
                "measurement_time": "115000",
                "instrument": "nivus",
                "q_total_ls": "50",
                "etime": "2026-01-22T11:58:20",
            },
            "2026-01-22T11:58:20",
            None,
            None,
            None,
        ),
    ],
)
def test_instrument_summary_normalizes_sih_metadata(
    instrument,
    row,
    expected_end,
    expected_start_scale,
    expected_end_scale,
    expected_operator,
):
    normalized = normalize_table(
        pd.DataFrame([row]),
        REGISTRY.get(instrument, "Summary"),
    )

    result = normalized.iloc[0]
    assert result["fecha_inicio"] == "2026-01-22 11:50:00"
    assert result["fecha_fin"] == expected_end
    for column, expected in (
        ("escala_inicio", expected_start_scale),
        ("escala_fin", expected_end_scale),
        ("operador", expected_operator),
    ):
        if expected is None:
            assert pd.isna(result[column]) or str(result[column]).strip().lower() in {
                "",
                "<na>",
                "nan",
                "none",
            }
        else:
            assert result[column] == expected
