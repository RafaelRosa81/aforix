from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from aforix.normalize.normalizer import normalize_table


CONFIGS = [
    Path("configs/normalization/flowtracker.yaml"),
    Path("configs/normalization/molinete.yaml"),
    Path("configs/normalization/nivus.yaml"),
]


def test_current_normalization_configs_do_not_generate_legacy_station_code():
    for path in CONFIGS:
        registry = yaml.safe_load(path.read_text(encoding="utf-8"))
        for table_name, spec in registry["tables"].items():
            policy = (spec.get("metadata_policy", {}) or {}).get("station_code", {}) or {}
            assert not policy.get("enabled", False), (
                f"{path}:{table_name} still enables legacy station_code generation"
            )


def test_normalized_output_does_not_force_station_code_when_not_requested():
    raw = pd.DataFrame(
        [
            {
                "station_id": "701150",
                "station_name": "Example",
                "measurement_date": "20260122",
                "measurement_time": "091500",
                "instrument": "nivus",
                "q_total_ls": "100.0",
            }
        ]
    )

    spec = {
        "metadata": {
            "station_id": {"sources": ["station_id"]},
            "station_name": {"sources": ["station_name"]},
            "measurement_date": {"sources": ["measurement_date"]},
            "measurement_time": {"sources": ["measurement_time"]},
            "instrument": {"sources": ["instrument"]},
        },
        "metadata_policy": {
            "station_id": {},
            "measurement_date": {"output_format": "%Y%m%d"},
            "measurement_time": {"output_format": "%H%M%S"},
        },
        "columns": {
            "q_total_ls": {"source": "q_total_ls", "dtype": "float"},
        },
        "required": [
            "station_id",
            "measurement_date",
            "measurement_time",
            "instrument",
            "q_total_ls",
        ],
        "transforms": [
            {"name": "strip_strings"},
            {"name": "numeric_commas_to_dots"},
            {"name": "enforce_dtypes"},
        ],
    }

    out = normalize_table(raw, spec)

    assert out.loc[0, "station_id"] == "701150"
    assert "station_code" not in out.columns
