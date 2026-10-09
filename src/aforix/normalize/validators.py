def validate_required_columns(df, required):
    missing = [col for col in required if col not in df.columns]

    if missing:
        raise ValueError(f"Missing required normalized columns: {missing}")


def _has_meaningful_values(series):
    if series.empty:
        return False

    if str(series.dtype) in {"object", "string"}:
        cleaned = series.astype("string").str.strip()
        cleaned = cleaned.mask(cleaned == "")
        return bool(cleaned.notna().any())

    return bool(series.notna().any())


def validate_qc_rules(df, qc):
    for col in qc.get("non_negative", []):
        if col in df.columns:
            invalid = df[col].dropna() < 0
            if invalid.any():
                raise ValueError(f"Column {col} contains negative values")

    for col in qc.get("non_empty", []):
        if col not in df.columns or not _has_meaningful_values(df[col]):
            raise ValueError(f"Column {col} is required to contain at least one value")

    return True
