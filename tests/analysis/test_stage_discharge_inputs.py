import pandas as pd

from aforix.analysis.stage_discharge.inputs import _normalize_measurement_date


def test_normalize_measurement_date_preserves_compact_yyyymmdd_values():
    values = pd.Series([20251217, "20250121", "2025-03-19", "11/30/2024"])

    result = _normalize_measurement_date(values)

    assert result.tolist() == [
        "2025-12-17",
        "2025-01-21",
        "2025-03-19",
        "2024-11-30",
    ]
