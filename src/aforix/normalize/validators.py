def validate_required_columns(df, required):
    missing = [col for col in required if col not in df.columns]

    if missing:
        raise ValueError(f"Missing required normalized columns: {missing}")


def validate_qc_rules(df, qc):
    for col in qc.get("non_negative", []):
        if col in df.columns:
            invalid = df[col].dropna() < 0
            if invalid.any():
                raise ValueError(f"Column {col} contains negative values")

    return True