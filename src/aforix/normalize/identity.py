"""Shared measurement identity for coherent filtering across tables."""
import pandas as pd

KEY_COLUMNS = ["instrument", "station_id", "measurement_date", "measurement_time"]


def measurement_keys(df: pd.DataFrame) -> pd.Series:
    """Use the same normalized, stripped identity across every table."""
    keys = df.reindex(columns=KEY_COLUMNS).astype("string")
    for column in KEY_COLUMNS:
        keys[column] = keys[column].str.strip()
    if keys.isna().any().any() or keys.eq("").any().any():
        raise ValueError("Measurement identity is incomplete; cannot safely exclude measurements")
    return keys.apply(tuple, axis=1)

