from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def _show(df: pd.DataFrame, columns: list[str], title: str) -> None:
    print("")
    print(title)
    print("-" * len(title))
    available = [c for c in columns if c in df.columns]
    if df.empty:
        print("(none)")
        return
    print(df[available].to_string(index=False))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize duplicate and range findings from the acceptance audit."
    )
    parser.add_argument(
        "--audit-dir",
        default="database_acceptance/validation/audit_outputs",
    )
    args = parser.parse_args()

    audit_dir = Path(args.audit_dir)
    duplicates_path = audit_dir / "duplicates_report.csv"
    ranges_path = audit_dir / "ranges_report.csv"

    duplicates = pd.read_csv(duplicates_path, dtype=str)
    ranges = pd.read_csv(ranges_path, dtype=str)

    dup = duplicates.loc[
        duplicates["status"].fillna("").astype(str).eq("duplicates")
    ].copy()

    flagged = ranges.loc[
        ranges["status"].fillna("").astype(str).eq("flagged")
    ].copy()

    print("Aforix acceptance audit findings")
    print("================================")
    print(f"Duplicate-report flagged tables: {len(dup)}")
    print(f"Range-report flagged checks    : {len(flagged)}")

    _show(
        dup,
        [
            "instrument",
            "group",
            "path",
            "key_columns_used",
            "n_rows",
            "n_duplicated_rows",
            "n_duplicate_keys",
        ],
        "Duplicate findings",
    )

    if not flagged.empty:
        for col in ["n_flagged", "min_value", "max_value"]:
            if col in flagged.columns:
                flagged[col] = pd.to_numeric(flagged[col], errors="coerce")

        summary_cols = [
            c for c in ["severity", "rule", "instrument", "group", "column"]
            if c in flagged.columns
        ]
        grouped = (
            flagged.groupby(summary_cols, dropna=False)
            .agg(
                flagged_checks=("status", "size"),
                flagged_data_rows=("n_flagged", "sum"),
                min_value=("min_value", "min"),
                max_value=("max_value", "max"),
            )
            .reset_index()
            .sort_values(summary_cols, kind="stable")
        )

        _show(
            grouped,
            [
                *summary_cols,
                "flagged_checks",
                "flagged_data_rows",
                "min_value",
                "max_value",
            ],
            "Range findings grouped",
        )

        error_warning = flagged.loc[
            flagged["severity"].fillna("").astype(str).isin(["error", "warning"])
        ].copy()
        _show(
            error_warning,
            [
                "severity",
                "instrument",
                "group",
                "column",
                "rule",
                "n_flagged",
                "min_value",
                "max_value",
                "path",
            ],
            "Error/warning range findings",
        )


if __name__ == "__main__":
    main()
