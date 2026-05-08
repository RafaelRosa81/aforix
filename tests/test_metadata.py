import pandas as pd

from aforix.metadata import (
    apply_metadata_policy,
    build_station_code,
    normalize_measurement_date,
    normalize_measurement_time,
    normalize_station_id,
)


def test_normalize_station_id_removes_prefix_and_keeps_digits():
    policy = {"remove_prefixes": ["P"], "digits_only": True}

    assert normalize_station_id("P11", policy) == "11"
    assert normalize_station_id("p912", policy) == "912"
    assert normalize_station_id("11", policy) == "11"


def test_build_station_code_adds_configured_prefix():
    assert build_station_code("11", {"prefix": "P"}) == "P11"
    assert build_station_code("P11", {"prefix": "P"}) == "P11"


def test_normalize_measurement_date_to_yyyymmdd():
    policy = {
        "input_formats": [
            "%Y%m%d",
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
        ],
        "output_format": "%Y%m%d",
    }

    assert normalize_measurement_date("20260119", policy) == "20260119"
    assert normalize_measurement_date("2026-01-19", policy) == "20260119"
    assert normalize_measurement_date("01/19/2026", policy) == "20260119"
    assert normalize_measurement_date("19/01/2026", policy) == "20260119"


def test_normalize_measurement_time_to_hhmmss():
    policy = {
        "input_formats": [
            "%H%M%S",
            "%H:%M:%S",
            "%H:%M",
        ],
        "output_format": "%H%M%S",
    }

    assert normalize_measurement_time("091500", policy) == "091500"
    assert normalize_measurement_time("91500", policy) == "091500"
    assert normalize_measurement_time("09:15:00", policy) == "091500"
    assert normalize_measurement_time("9:15", policy) == "091500"


def test_apply_metadata_policy_normalizes_traceability_columns():
    df = pd.DataFrame(
        [
            {
                "station_id": "P11",
                "measurement_date": "01/19/2026",
                "measurement_time": "9:15:00",
            }
        ]
    )

    policy = {
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
    }

    out = apply_metadata_policy(df, policy)

    assert out.loc[0, "station_id"] == "11"
    assert out.loc[0, "station_code"] == "P11"
    assert out.loc[0, "measurement_date"] == "20260119"
    assert out.loc[0, "measurement_time"] == "091500"
