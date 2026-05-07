import pandas as pd

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
