from __future__ import annotations

from typing import Any

import pandas as pd

from aforix.metadata import apply_metadata_policy
from aforix.normalize.transforms import apply_transforms
from aforix.normalize.validators import validate_required_columns, validate_qc_rules


TRACEABILITY_COLUMNS = [
    "station_id",
    "station_name",
    "measurement_date",
    "measurement_time",
    "instrument",
    "source_file",
    "source_run_dir",
    "run_id",
]


def _empty_series(df: pd.DataFrame) -> pd.Series:
    return pd.Series([pd.NA] * len(df), index=df.index)


def _coalesce_sources(df: pd.DataFrame, sources: list[str]) -> pd.Series:
    valid = [col for col in sources if col in df.columns]

    if not valid:
        return _empty_series(df)

    out = df[valid[0]].copy()

    for col in valid[1:]:
        out = out.combine_first(df[col])

    return out


def _get_sources(col_spec: dict[str, Any]) -> list[str]:
    if "sources" in col_spec:
        sources = col_spec["sources"]

        if not isinstance(sources, list):
            raise ValueError("'sources' must be a list.")

        return [str(source) for source in sources]

    if "source" in col_spec:
        return [str(col_spec["source"])]

    raise ValueError("Column spec must define 'source' or 'sources'.")


def _ensure_traceability_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for col in TRACEABILITY_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

        df[col] = df[col].astype("string")

    remaining = [col for col in df.columns if col not in TRACEABILITY_COLUMNS]

    return df[TRACEABILITY_COLUMNS + remaining]


def _apply_metadata_sources(
    out: pd.DataFrame,
    df_raw: pd.DataFrame,
    metadata_spec: dict[str, Any],
) -> pd.DataFrame:
    """Populate traceability columns from explicit YAML metadata sources.

    `metadata` answers where a traceability value comes from.
    `metadata_policy` later answers how that value is normalized/formatted.
    """
    out = out.copy()

    if not metadata_spec:
        return out

    if not isinstance(metadata_spec, dict):
        raise ValueError("'metadata' must be a mapping/dictionary.")

    for canonical_col, col_spec in metadata_spec.items():
        if not isinstance(col_spec, dict):
            raise ValueError(f"Invalid metadata spec for '{canonical_col}'.")

        sources = _get_sources(col_spec)
        values = _coalesce_sources(df_raw, sources)
        overwrite = bool(col_spec.get("overwrite", False))

        if canonical_col not in out.columns or overwrite:
            out[canonical_col] = values
        else:
            out[canonical_col] = out[canonical_col].combine_first(values)

    return out


def _to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _apply_derived_columns(
    df: pd.DataFrame,
    derived_spec: dict[str, Any],
) -> pd.DataFrame:
    df = df.copy()

    if not derived_spec:
        return df

    if not isinstance(derived_spec, dict):
        raise ValueError("'derived' must be a mapping/dictionary.")

    for target_col, rule in derived_spec.items():
        if not isinstance(rule, dict):
            raise ValueError(f"Invalid derived rule for '{target_col}'.")

        source_col = rule.get("from")
        operation = rule.get("operation")
        value = rule.get("value")

        if not source_col:
            raise ValueError(f"Derived column '{target_col}' must define 'from'.")

        if source_col not in df.columns:
            df[target_col] = pd.NA
            continue

        if operation == "copy":
            df[target_col] = df[source_col]
            continue

        source = _to_numeric(df[source_col])

        if operation == "divide":
            df[target_col] = source / float(value)

        elif operation == "multiply":
            df[target_col] = source * float(value)

        elif operation == "add":
            df[target_col] = source + float(value)

        elif operation == "subtract":
            df[target_col] = source - float(value)

        else:
            raise ValueError(
                f"Unsupported derived operation for '{target_col}': {operation}"
            )

    return df


def normalize_table(
    df_raw: pd.DataFrame,
    spec: dict[str, Any],
) -> pd.DataFrame:
    columns_spec = spec.get("columns", {})

    if not isinstance(columns_spec, dict):
        raise ValueError("Normalization spec must contain a 'columns' mapping.")

    out = pd.DataFrame(index=df_raw.index)

    for canonical_col, col_spec in columns_spec.items():
        if not isinstance(col_spec, dict):
            raise ValueError(f"Invalid spec for column '{canonical_col}'.")

        sources = _get_sources(col_spec)
        out[canonical_col] = _coalesce_sources(df_raw, sources)

    out = _apply_metadata_sources(
        out,
        df_raw,
        spec.get("metadata", {}),
    )

    for col in TRACEABILITY_COLUMNS:
        if col not in out.columns and col in df_raw.columns:
            out[col] = df_raw[col]

    out = _ensure_traceability_columns(out)

    out = _apply_derived_columns(
        out,
        spec.get("derived", {}),
    )

    out = apply_metadata_policy(
        out,
        spec.get("metadata_policy", {}),
    )

    validate_required_columns(out, spec.get("required", []))

    out = apply_transforms(
        out,
        spec.get("transforms", []),
        columns_spec,
    )

    validate_qc_rules(out, spec.get("qc", {}))

    out = _ensure_traceability_columns(out)

    return out
