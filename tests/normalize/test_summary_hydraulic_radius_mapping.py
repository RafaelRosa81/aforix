from pathlib import Path

import pandas as pd
import pytest

from aforix.normalize.normalizer import normalize_table
from aforix.normalize.registry import NormalizationRegistry


@pytest.mark.parametrize(
    ("instrument", "source_field", "raw_value", "expected"),
    [
        ("nivus", "rh [m]", "0.37", 0.37),
        ("molinete", "radio_hidraulico_m", "0.245", 0.245),
    ],
)
def test_existing_instrument_hydraulic_radius_maps_to_summary(
    instrument, source_field, raw_value, expected
):
    registry = NormalizationRegistry(Path("configs/normalization"))
    spec = registry.get(instrument, "Summary")
    row = {
        "station_id": "7071",
        "measurement_date": "20260120",
        "measurement_time": "142300",
        "instrument": instrument,
        "q_total_m3s": "0.08",
        "q [l/s]": "80",
        source_field: raw_value,
    }
    normalized = normalize_table(pd.DataFrame([row]), spec)
    assert "hydraulic_radius_m" in normalized.columns
    assert normalized.loc[0, "hydraulic_radius_m"] == pytest.approx(expected)
