from pathlib import Path

import pandas as pd
import pytest

from aforix.normalize.normalizer import normalize_table
from aforix.normalize.registry import NormalizationRegistry


SUMMARY_FIELDS = {
    "rev_en_s": 60.0,
    "a_1": 0.1032,
    "a_2": 0.0558,
    "a_3": 0.0533,
    "b_1": 0.022,
    "b_2": 0.035,
    "b_3": 0.059,
    "k_lim_1": 3.06,
    "k_lim_2": 9.60,
}

POINTS_FIELDS = {
    "rev_1_s": 0.0,
    "rev_2_s": 31.0,
    "rev_3_s": None,
    "vel_point_1_ms": 0.0,
    "vel_point_2_ms": 0.07532,
    "vel_point_3_ms": None,
}


@pytest.mark.parametrize(
    ("group", "instrumental_fields", "additional_fields"),
    [
        (
            "Summary",
            SUMMARY_FIELDS,
            {"q_total_m3s": "0.082686"},
        ),
        (
            "Points",
            POINTS_FIELDS,
            {
                "point_index": "1",
                "point_label": "V1",
                "progr_m": "0.7",
                "width_m": "2.9",
                "prof_m": "0.25",
                "vel_media_vert_ms": "0.07532",
                "percent_q": "10",
            },
        ),
    ],
)
def test_molinete_instrumental_fields_survive_normalization(
    group, instrumental_fields, additional_fields
):
    registry = NormalizationRegistry(Path("configs/normalization"))
    spec = registry.get("molinete", group)

    raw_row = {
        "station_id": "7071",
        "measurement_date": "20260120",
        "measurement_time": "142300",
        "instrument": "molinete",
        **additional_fields,
        **instrumental_fields,
    }

    raw = pd.DataFrame([raw_row])
    normalized = normalize_table(raw, spec)

    assert len(normalized) == 1

    for field, expected in instrumental_fields.items():
        assert field in normalized.columns, (
            f"Campo instrumental perdido: {group}.{field}"
        )

        actual = normalized.loc[0, field]

        if expected is None:
            assert pd.isna(actual), (
                f"{group}.{field}: se esperaba un valor ausente"
            )
        else:
            assert pd.notna(actual)
            assert float(actual) == pytest.approx(expected), (
                f"{group}.{field}: valor instrumental alterado"
            )
