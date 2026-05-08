from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


TRACEABILITY_COLUMNS = [
    "station_id",
    "station_code",
    "station_name",
    "measurement_date",
    "measurement_time",
    "instrument",
    "source_file",
    "source_run_dir",
    "run_id",
]

RAW_TRACEABILITY_COLUMNS = [
    "station_id",
    "station_name",
    "measurement_date",
    "measurement_time",
    "instrument",
    "source_file",
    "source_run_dir",
    "run_id",
]

NORMALIZED_SUMMARY_REQUIRED = [
    "station_id",
    "station_code",
    "station_name",
    "measurement_date",
    "measurement_time",
    "instrument",
    "source_file",
    "source_run_dir",
    "run_id",
    "q_total_m3s",
    "q_total_ls",
    "area_total_m2",
]

NORMALIZED_POINTS_REQUIRED = [
    "station_id",
    "station_code",
    "station_name",
    "measurement_date",
    "measurement_time",
    "instrument",
    "source_file",
    "source_run_dir",
    "run_id",
    "point_index",
    "distance_m",
    "depth_m",
    "area_m2",
    "q_m3s",
    "q_ls",
]

KEY_COLUMNS = ["instrument", "station_id", "measurement_date", "measurement_time"]
GROUP_KEY_CANDIDATES = {
    "Summary": [],
    "Points": ["point_index", "distance_m"],
    "Sections": ["section_index", "section_id", "distance_m"],
    "Gates": [],
}
HYDRAULIC_DEDUP_CANDIDATES = [
    "instrument",
    "station_id",
    "measurement_date",
    "measurement_time",
    "point_index",
    "distance_m",
    "depth_m",
    "area_m2",
    "q_m3s",
    "q_ls",
]
DEFAULT_TOLERANCE_PCT = 1.0
DEFAULT_ABS_TOL = 1e-9
DEFAULT_Q_M3S_ABS_TOL = 5e-4
DEFAULT_Q_LS_ABS_TOL = 0.5
DEFAULT_AREA_M2_ABS_TOL = 1e-3


@dataclass(frozen=True)
class TableRef:
    stage: str
    instrument: str
    group: str
    path: Path
    layout: str


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str)


def _to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _empty_report() -> pd.DataFrame:
    return pd.DataFrame()


def _discover_tables(root: Path, *, stage: str) -> list[TableRef]:
    tables: list[TableRef] = []
    if not root.exists():
        return tables

    for instrument_dir in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith("_")):
        instrument = instrument_dir.name

        for csv_path in sorted(instrument_dir.glob("*.csv")):
            tables.append(
                TableRef(
                    stage=stage,
                    instrument=instrument,
                    group=csv_path.stem,
                    path=csv_path,
                    layout="concat_file",
                )
            )

        for group_dir in sorted(p for p in instrument_dir.iterdir() if p.is_dir()):
            group = group_dir.name
            for csv_path in sorted(group_dir.glob("*.csv")):
                tables.append(
                    TableRef(
                        stage=stage,
                        instrument=instrument,
                        group=group,
                        path=csv_path,
                        layout="file_group",
                    )
                )

    return tables


def _expected_columns(stage: str, group: str) -> list[str]:
    if stage == "raw_canonical":
        return RAW_TRACEABILITY_COLUMNS
    if group == "Summary":
        return NORMALIZED_SUMMARY_REQUIRED
    if group == "Points":
        return NORMALIZED_POINTS_REQUIRED
    return TRACEABILITY_COLUMNS


def _duplicate_key_columns(df: pd.DataFrame, group: str) -> tuple[list[str], list[str]]:
    base_missing = [col for col in KEY_COLUMNS if col not in df.columns]
    if base_missing:
        return [], base_missing

    if group == "Gates":
        return [], []

    key_cols = list(KEY_COLUMNS)
    missing_group_candidates: list[str] = []

    for candidate in GROUP_KEY_CANDIDATES.get(group, []):
        if candidate in df.columns:
            key_cols.append(candidate)
            return key_cols, []
        missing_group_candidates.append(candidate)

    if group != "Summary" and GROUP_KEY_CANDIDATES.get(group):
        return key_cols, missing_group_candidates

    return key_cols, []


def _deduplicate_points_for_hydraulic_audit(points: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    rows_before = len(points)
    key_cols = [col for col in HYDRAULIC_DEDUP_CANDIDATES if col in points.columns]

    if not key_cols:
        return points, rows_before, rows_before

    deduped = points.drop_duplicates(subset=key_cols, keep="first").copy()
    return deduped, rows_before, len(deduped)


def _abs_tolerance_for_check(check_name: str) -> float:
    if check_name == "q_m3s":
        return DEFAULT_Q_M3S_ABS_TOL
    if check_name == "q_ls":
        return DEFAULT_Q_LS_ABS_TOL
    if check_name == "area_m2":
        return DEFAULT_AREA_M2_ABS_TOL
    return DEFAULT_ABS_TOL


def audit_columns(tables: Iterable[TableRef]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for table in tables:
        try:
            df = _read_csv(table.path)
        except Exception as exc:
            rows.append(
                {
                    "stage": table.stage,
                    "instrument": table.instrument,
                    "group": table.group,
                    "path": str(table.path),
                    "status": "read_error",
                    "detail": str(exc),
                }
            )
            continue

        expected = _expected_columns(table.stage, table.group)
        missing = [col for col in expected if col not in df.columns]
        empty_expected = [
            col
            for col in expected
            if col in df.columns and df[col].isna().all()
        ]

        rows.append(
            {
                "stage": table.stage,
                "instrument": table.instrument,
                "group": table.group,
                "layout": table.layout,
                "path": str(table.path),
                "n_rows": len(df),
                "n_columns": len(df.columns),
                "status": "ok" if not missing else "missing_columns",
                "missing_columns": ";".join(missing),
                "empty_expected_columns": ";".join(empty_expected),
                "columns": ";".join(df.columns.astype(str)),
            }
        )

    return pd.DataFrame(rows)


def audit_duplicates(normalized_root: Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for instrument_dir in sorted(p for p in normalized_root.iterdir() if p.is_dir() and not p.name.startswith("_")) if normalized_root.exists() else []:
        instrument = instrument_dir.name
        for group in ["Summary", "Points", "Sections", "Gates"]:
            candidates = []
            concat_file = instrument_dir / f"{group}.csv"
            group_dir = instrument_dir / group
            if concat_file.exists():
                candidates.append(concat_file)
            if group_dir.exists():
                candidates.extend(sorted(group_dir.glob("*.csv")))

            for path in candidates:
                try:
                    df = _read_csv(path)
                except Exception as exc:
                    rows.append(
                        {
                            "instrument": instrument,
                            "group": group,
                            "path": str(path),
                            "status": "read_error",
                            "detail": str(exc),
                        }
                    )
                    continue

                if group == "Gates":
                    rows.append(
                        {
                            "instrument": instrument,
                            "group": group,
                            "path": str(path),
                            "status": "not_checked",
                            "detail": "No reliable unique key has been defined for Gates yet.",
                            "n_rows": len(df),
                        }
                    )
                    continue

                key_cols, missing_key_columns = _duplicate_key_columns(df, group)
                if missing_key_columns and not key_cols:
                    rows.append(
                        {
                            "instrument": instrument,
                            "group": group,
                            "path": str(path),
                            "status": "missing_key_columns",
                            "missing_key_columns": ";".join(missing_key_columns),
                            "n_rows": len(df),
                        }
                    )
                    continue

                if missing_key_columns and group != "Summary":
                    rows.append(
                        {
                            "instrument": instrument,
                            "group": group,
                            "path": str(path),
                            "status": "missing_group_key_columns",
                            "missing_key_columns": ";".join(missing_key_columns),
                            "key_columns_used": ";".join(key_cols),
                            "n_rows": len(df),
                        }
                    )
                    continue

                duplicated = df.duplicated(key_cols, keep=False)
                n_duplicated = int(duplicated.sum())
                rows.append(
                    {
                        "instrument": instrument,
                        "group": group,
                        "path": str(path),
                        "status": "duplicates" if n_duplicated else "ok",
                        "n_rows": len(df),
                        "key_columns_used": ";".join(key_cols),
                        "n_duplicated_rows": n_duplicated,
                        "n_duplicate_keys": int(df.loc[duplicated, key_cols].drop_duplicates().shape[0]) if n_duplicated else 0,
                    }
                )

    return pd.DataFrame(rows)


def _relative_diff_pct(observed: float, expected: float, *, abs_tol: float) -> float:
    denominator = max(abs(expected), abs_tol)
    return abs(observed - expected) / denominator * 100.0


def _load_normalized_summary(normalized_root: Path, instrument: str) -> pd.DataFrame | None:
    path = normalized_root / instrument / "Summary.csv"
    if not path.exists():
        return None
    df = _read_csv(path)
    if "instrument" not in df.columns:
        df["instrument"] = instrument
    return df


def _load_normalized_points(normalized_root: Path, instrument: str) -> pd.DataFrame | None:
    concat_path = normalized_root / instrument / "Points.csv"
    group_dir = normalized_root / instrument / "Points"

    frames: list[pd.DataFrame] = []
    if concat_path.exists():
        frames.append(_read_csv(concat_path))
    elif group_dir.exists():
        for path in sorted(group_dir.glob("*.csv")):
            frames.append(_read_csv(path))

    if not frames:
        return None

    df = pd.concat(frames, ignore_index=True, sort=False)
    if "instrument" not in df.columns:
        df["instrument"] = instrument
    return df


def audit_hydraulic_consistency(
    normalized_root: Path,
    *,
    tolerance_pct: float = DEFAULT_TOLERANCE_PCT,
    abs_tol: float = DEFAULT_ABS_TOL,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    if not normalized_root.exists():
        return _empty_report()

    instruments = sorted(p.name for p in normalized_root.iterdir() if p.is_dir() and not p.name.startswith("_"))

    for instrument in instruments:
        summary = _load_normalized_summary(normalized_root, instrument)
        points = _load_normalized_points(normalized_root, instrument)

        if summary is None or points is None:
            rows.append(
                {
                    "instrument": instrument,
                    "status": "missing_summary_or_points",
                    "has_summary": summary is not None,
                    "has_points": points is not None,
                }
            )
            continue

        missing_summary_keys = [col for col in KEY_COLUMNS if col not in summary.columns]
        missing_points_keys = [col for col in KEY_COLUMNS if col not in points.columns]
        if missing_summary_keys or missing_points_keys:
            rows.append(
                {
                    "instrument": instrument,
                    "status": "missing_key_columns",
                    "missing_summary_keys": ";".join(missing_summary_keys),
                    "missing_points_keys": ";".join(missing_points_keys),
                }
            )
            continue

        points, points_rows_raw, points_rows_after_dedup = _deduplicate_points_for_hydraulic_audit(points)
        points_rows_dropped = points_rows_raw - points_rows_after_dedup

        point_aggs: dict[str, tuple[str, str]] = {}
        if "q_m3s" in points.columns:
            points["q_m3s_num"] = _to_numeric(points["q_m3s"])
            point_aggs["points_q_m3s_sum"] = ("q_m3s_num", "sum")
        if "q_ls" in points.columns:
            points["q_ls_num"] = _to_numeric(points["q_ls"])
            point_aggs["points_q_ls_sum"] = ("q_ls_num", "sum")
        if "area_m2" in points.columns:
            points["area_m2_num"] = _to_numeric(points["area_m2"])
            point_aggs["points_area_m2_sum"] = ("area_m2_num", "sum")

        if not point_aggs:
            rows.append(
                {
                    "instrument": instrument,
                    "status": "missing_points_numeric_columns",
                }
            )
            continue

        points_agg = points.groupby(KEY_COLUMNS, dropna=False).agg(**point_aggs).reset_index()
        merged = summary.merge(points_agg, on=KEY_COLUMNS, how="left", indicator=True)

        for _, row in merged.iterrows():
            base = {
                "instrument": instrument,
                "station_id": row.get("station_id"),
                "measurement_date": row.get("measurement_date"),
                "measurement_time": row.get("measurement_time"),
                "merge_status": row.get("_merge"),
                "points_rows_raw": points_rows_raw,
                "points_rows_after_dedup": points_rows_after_dedup,
                "points_rows_dropped_as_duplicates": points_rows_dropped,
            }

            checks = [
                ("q_m3s", "q_total_m3s", "points_q_m3s_sum"),
                ("q_ls", "q_total_ls", "points_q_ls_sum"),
                ("area_m2", "area_total_m2", "points_area_m2_sum"),
            ]

            any_check = False
            for check_name, summary_col, points_col in checks:
                if summary_col not in merged.columns or points_col not in merged.columns:
                    continue
                summary_val = pd.to_numeric(pd.Series([row.get(summary_col)]), errors="coerce").iloc[0]
                points_val = pd.to_numeric(pd.Series([row.get(points_col)]), errors="coerce").iloc[0]
                check_abs_tol = max(abs_tol, _abs_tolerance_for_check(check_name))
                if pd.isna(summary_val) or pd.isna(points_val):
                    status = "missing_values"
                    diff_pct = pd.NA
                    diff_abs = pd.NA
                    within_abs_tolerance = pd.NA
                    within_pct_tolerance = pd.NA
                else:
                    diff_abs = float(summary_val - points_val)
                    diff_abs_magnitude = abs(diff_abs)
                    diff_pct = _relative_diff_pct(float(points_val), float(summary_val), abs_tol=check_abs_tol)
                    within_abs_tolerance = diff_abs_magnitude <= check_abs_tol
                    within_pct_tolerance = diff_pct <= tolerance_pct
                    status = "ok" if within_abs_tolerance or within_pct_tolerance else "mismatch"
                rows.append(
                    {
                        **base,
                        "check": check_name,
                        "summary_column": summary_col,
                        "points_column": points_col,
                        "summary_value": summary_val,
                        "points_sum": points_val,
                        "diff_abs_summary_minus_points": diff_abs,
                        "diff_pct": diff_pct,
                        "tolerance_pct": tolerance_pct,
                        "abs_tolerance": check_abs_tol,
                        "within_abs_tolerance": within_abs_tolerance,
                        "within_pct_tolerance": within_pct_tolerance,
                        "status": status,
                    }
                )
                any_check = True

            if not any_check:
                rows.append({**base, "status": "no_comparable_columns"})

    return pd.DataFrame(rows)


def audit_unit_consistency(normalized_root: Path, *, tolerance_pct: float = DEFAULT_TOLERANCE_PCT) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    tables = _discover_tables(normalized_root, stage="normalized")

    for table in tables:
        try:
            df = _read_csv(table.path)
        except Exception as exc:
            rows.append(
                {
                    "instrument": table.instrument,
                    "group": table.group,
                    "path": str(table.path),
                    "status": "read_error",
                    "detail": str(exc),
                }
            )
            continue

        pairs = [
            ("q_total_m3s", "q_total_ls"),
            ("q_m3s", "q_ls"),
        ]
        for m3s_col, ls_col in pairs:
            if m3s_col not in df.columns or ls_col not in df.columns:
                continue
            m3s = _to_numeric(df[m3s_col])
            ls = _to_numeric(df[ls_col])
            expected_ls = m3s * 1000.0
            denominator = expected_ls.abs().clip(lower=DEFAULT_ABS_TOL)
            diff_pct = ((ls - expected_ls).abs() / denominator) * 100.0
            bad = diff_pct > tolerance_pct
            rows.append(
                {
                    "instrument": table.instrument,
                    "group": table.group,
                    "path": str(table.path),
                    "check": f"{m3s_col}_to_{ls_col}",
                    "n_rows": len(df),
                    "n_checked": int(diff_pct.notna().sum()),
                    "n_mismatch": int(bad.sum()),
                    "max_diff_pct": float(diff_pct.max()) if diff_pct.notna().any() else pd.NA,
                    "status": "mismatch" if bad.any() else "ok",
                }
            )

    return pd.DataFrame(rows)


def audit_ranges(normalized_root: Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    tables = _discover_tables(normalized_root, stage="normalized")

    rules = {
        "area_total_m2": {"min": 0, "severity": "error"},
        "area_m2": {"min": 0, "severity": "error"},
        "depth_mean_m": {"min": 0, "severity": "error"},
        "depth_m": {"min": 0, "severity": "error"},
        "temperature_c": {"min": -5, "max": 45, "severity": "warning"},
        "q_total_m3s": {"severity": "info"},
        "q_m3s": {"severity": "info"},
    }

    for table in tables:
        try:
            df = _read_csv(table.path)
        except Exception as exc:
            rows.append(
                {
                    "instrument": table.instrument,
                    "group": table.group,
                    "path": str(table.path),
                    "status": "read_error",
                    "detail": str(exc),
                }
            )
            continue

        for col, rule in rules.items():
            if col not in df.columns:
                continue
            values = _to_numeric(df[col])
            invalid = pd.Series(False, index=df.index)
            if "min" in rule:
                invalid |= values < float(rule["min"])
            if "max" in rule:
                invalid |= values > float(rule["max"])
            if col.startswith("q"):
                negative = values < 0
                rows.append(
                    {
                        "instrument": table.instrument,
                        "group": table.group,
                        "path": str(table.path),
                        "column": col,
                        "rule": "negative_flow_observed",
                        "severity": "info",
                        "n_rows": len(df),
                        "n_flagged": int(negative.sum()),
                        "min_value": float(values.min()) if values.notna().any() else pd.NA,
                        "max_value": float(values.max()) if values.notna().any() else pd.NA,
                        "status": "flagged" if negative.any() else "ok",
                    }
                )
                continue
            rows.append(
                {
                    "instrument": table.instrument,
                    "group": table.group,
                    "path": str(table.path),
                    "column": col,
                    "rule": "range",
                    "severity": rule.get("severity", "warning"),
                    "n_rows": len(df),
                    "n_flagged": int(invalid.sum()),
                    "min_value": float(values.min()) if values.notna().any() else pd.NA,
                    "max_value": float(values.max()) if values.notna().any() else pd.NA,
                    "status": "flagged" if invalid.any() else "ok",
                }
            )

    return pd.DataFrame(rows)


def write_report(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def summarize_reports(reports: dict[str, pd.DataFrame]) -> str:
    lines = ["Aforix pipeline output audit", ""]
    for name, df in reports.items():
        lines.append(f"{name}: {len(df)} rows")
        if "status" in df.columns and not df.empty:
            counts = df["status"].value_counts(dropna=False).to_dict()
            lines.append(f"  status_counts: {counts}")
        lines.append("")
    return "\n".join(lines)


def run_audit(
    *,
    raw_root: Path,
    normalized_root: Path,
    output_dir: Path,
    tolerance_pct: float,
    abs_tol: float,
) -> Path:
    raw_tables = _discover_tables(raw_root, stage="raw_canonical")
    normalized_tables = _discover_tables(normalized_root, stage="normalized")

    reports = {
        "raw_column_report": audit_columns(raw_tables),
        "normalized_column_report": audit_columns(normalized_tables),
        "duplicates_report": audit_duplicates(normalized_root),
        "hydraulic_consistency_report": audit_hydraulic_consistency(
            normalized_root,
            tolerance_pct=tolerance_pct,
            abs_tol=abs_tol,
        ),
        "unit_consistency_report": audit_unit_consistency(
            normalized_root,
            tolerance_pct=tolerance_pct,
        ),
        "ranges_report": audit_ranges(normalized_root),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    for name, df in reports.items():
        write_report(df, output_dir / f"{name}.csv")

    summary = summarize_reports(reports)
    (output_dir / "summary.txt").write_text(summary, encoding="utf-8")

    print(summary)
    print(f"Audit reports written to: {output_dir}")
    return output_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit Aforix raw_canonical and normalized pipeline outputs.",
    )
    parser.add_argument(
        "--raw-root",
        default="database/raw_canonical",
        help="Path to database/raw_canonical.",
    )
    parser.add_argument(
        "--normalized-root",
        default="database/normalized",
        help="Path to database/normalized.",
    )
    parser.add_argument(
        "--output-dir",
        default="database/validation/audit_outputs",
        help="Directory where audit reports will be written.",
    )
    parser.add_argument(
        "--tolerance-pct",
        type=float,
        default=DEFAULT_TOLERANCE_PCT,
        help="Relative tolerance percentage for hydraulic and unit checks.",
    )
    parser.add_argument(
        "--abs-tol",
        type=float,
        default=DEFAULT_ABS_TOL,
        help="Base absolute tolerance for hydraulic checks. Check-specific defaults may be larger.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_audit(
        raw_root=Path(args.raw_root),
        normalized_root=Path(args.normalized_root),
        output_dir=Path(args.output_dir),
        tolerance_pct=args.tolerance_pct,
        abs_tol=args.abs_tol,
    )


if __name__ == "__main__":
    main()
