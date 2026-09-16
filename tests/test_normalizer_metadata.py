import pandas as pd
import pytest
import yaml

from aforix.canonical.normalizer import normalize_table


def test_normalize_table_uses_metadata_sources_and_policy():
    df_raw = pd.DataFrame(
        [
            {
                "estacion": "P11",
                "nombre": "Paso 11",
                "fecha": "01/19/2026",
                "hora_ini": "9:15:00",
                "instrument": "molinete",
                "raw_source_file": "P11.xlsx",
                "q_m3s": "0.082686",
            }
        ]
    )

    spec = {
        "metadata": {
            "station_id": {"sources": ["station_id", "estacion"]},
            "station_name": {"sources": ["station_name", "nombre"]},
            "measurement_date": {"sources": ["measurement_date", "fecha"]},
            "measurement_time": {"sources": ["measurement_time", "hora_ini"]},
            "instrument": {"sources": ["instrument"]},
            "source_file": {"sources": ["source_file", "raw_source_file"]},
        },
        "metadata_policy": {
            "station_id": {"remove_prefixes": ["P"], "digits_only": True},
            "station_code": {"enabled": True, "prefix": "P"},
            "measurement_date": {
                "input_formats": ["%m/%d/%Y"],
                "output_format": "%Y%m%d",
            },
            "measurement_time": {
                "input_formats": ["%H:%M:%S"],
                "output_format": "%H%M%S",
            },
        },
        "columns": {
            "q_total_m3s": {"source": "q_m3s", "dtype": "float"},
        },
        "required": [
            "station_id",
            "measurement_date",
            "measurement_time",
            "instrument",
            "q_total_m3s",
        ],
        "transforms": [
            {"name": "strip_strings"},
            {"name": "numeric_commas_to_dots"},
            {"name": "enforce_dtypes"},
        ],
    }

    out = normalize_table(df_raw, spec)

    assert out.loc[0, "station_id"] == "11"
    assert out.loc[0, "station_code"] == "P11"
    assert out.loc[0, "station_name"] == "Paso 11"
    assert out.loc[0, "measurement_date"] == "20260119"
    assert out.loc[0, "measurement_time"] == "091500"
    assert out.loc[0, "instrument"] == "molinete"
    assert out.loc[0, "source_file"] == "P11.xlsx"
    assert out.loc[0, "q_total_m3s"] == 0.082686


def test_flowtracker_summary_preserves_canonical_area_total_m2():
    with open("configs/normalization/flowtracker.yaml", encoding="utf-8") as f:
        registry = yaml.safe_load(f)

    spec = registry["tables"]["Summary"]
    df_raw = pd.DataFrame(
        [
            {
                "station_id": "7001",
                "station_name": "Prueba",
                "measurement_date": "20260122",
                "measurement_time": "142258",
                "instrument": "flowtracker",
                "area_total_m2": "4.188",
                "total_discharge_m3_s": "0.0458",
            }
        ]
    )

    out = normalize_table(df_raw, spec)

    assert out.loc[0, "area_total_m2"] == 4.188


@pytest.mark.parametrize(
    ("raw_column", "canonical_column", "raw_value", "expected"),
    [
        ("ancho_total_m", "width_total_m", "2.9", 2.9),
        ("velocidad_media_m_s", "velocity_mean_m_s", "0.1168", 0.1168),
        ("calado_medido_m", "depth_mean_m", "0.135", 0.135),
        ("temp_promedio_degc", "temperature_c", "24.77", 24.77),
    ],
)
def test_flowtracker_summary_preserves_spanish_hydraulic_aliases(
    raw_column, canonical_column, raw_value, expected
):
    with open("configs/normalization/flowtracker.yaml", encoding="utf-8") as f:
        registry = yaml.safe_load(f)

    spec = registry["tables"]["Summary"]
    df_raw = pd.DataFrame(
        [
            {
                "station_id": "7001",
                "station_name": "Prueba",
                "measurement_date": "20260122",
                "measurement_time": "142258",
                "instrument": "flowtracker",
                "total_discharge_m3_s": "0.0458",
                raw_column: raw_value,
            }
        ]
    )

    out = normalize_table(df_raw, spec)

    assert out.loc[0, canonical_column] == expected
