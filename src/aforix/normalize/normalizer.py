import pandas as pd

from aforix.normalize.transforms import apply_transforms
from aforix.normalize.validators import validate_required_columns, validate_qc_rules


def normalize_table(
    df_raw: pd.DataFrame,
    spec: dict,
) -> pd.DataFrame:
    columns_spec = spec["columns"]

    rename_map = {}
    output_columns = []

    for canonical_col, col_spec in columns_spec.items():
        source_col = col_spec["source"]

        if source_col in df_raw.columns:
            rename_map[source_col] = canonical_col
            output_columns.append(canonical_col)

    df = df_raw.rename(columns=rename_map)

    df = df[output_columns].copy()

    validate_required_columns(df, spec.get("required", []))

    df = apply_transforms(df, spec.get("transforms", []), columns_spec)

    validate_qc_rules(df, spec.get("qc", {}))

    return df