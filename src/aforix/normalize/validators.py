from pandas.api.types import is_string_dtype

def validate_required_columns(df, required):
    missing = [col for col in required if col not in df.columns]

    if missing:
        raise ValueError(f"Missing required normalized columns: {missing}")


def _all_values_meaningful(series):
    if series.empty:
        return False

    if is_string_dtype(series.dtype) or str(series.dtype) == "object":
        cleaned = series.astype("string").str.strip()
        cleaned = cleaned.mask(cleaned == "")
        return bool(cleaned.notna().all())

    return bool(series.notna().all())


def validate_qc_rules(df, qc):
    for col in qc.get("non_negative", []):
        if col in df.columns:
            invalid = df[col].dropna() < 0
            if invalid.any():
                raise ValueError(f"Column {col} contains negative values")

    for col in qc.get("non_empty", []):
        if col not in df.columns or not _all_values_meaningful(df[col]):
            raise ValueError(
                f"Column {col} is required to contain a value in every row"
            )

    return True
