from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from aforix.validation.common import DEFAULT_KEYS, read_table, safe_numeric, write_report


def run(
    *,
    input_dir: Path,
    output_dir: Path,
    validation_cfg: dict[str, Any],
) -> tuple[Path, pd.DataFrame]:
    keys = validation_cfg.get("keys", DEFAULT_KEYS)
    cfg = validation_cfg.get("hydraulic_consistency", {}) or {}

    q_tolerance_pct = float(cfg.get("q_tolerance_pct", 1.0))
    area_tolerance_pct = float(cfg.get("area_tolerance_pct", 1.0))

    summary = read_table(input_dir, "Summary")
    points = read_table(input_dir, "Points")

    if summary is None or points is None:
        report = pd.DataFrame(
            [
                {
                    "status": "missing_table",
                    "message": "Summary.csv or Points.csv not found.",
                }
            ]
        )
        path = write_report(report, output_dir, "hydraulic_consistency_summary_points.csv")
        return path, report

    required_summary = [*keys, "q_total_m3s", "q_total_ls", "area_total_m2"]
    required_points = [*keys, "q_m3s", "q_ls", "area_m2"]

    missing_summary = [col for col in required_summary if col not in summary.columns]
    missing_points = [col for col in required_points if col not in points.columns]

    if missing_summary or missing_points:
        report = pd.DataFrame(
            [
                {
                    "status": "missing_columns",
                    "missing_summary_columns": ",".join(missing_summary),
                    "missing_points_columns": ",".join(missing_points),
                }
            ]
        )
        path = write_report(report, output_dir, "hydraulic_consistency_summary_points.csv")
        return path, report

    summary = summary.copy()
    points = points.copy()

    summary["q_total_m3s"] = safe_numeric(summary["q_total_m3s"])
    summary["q_total_ls"] = safe_numeric(summary["q_total_ls"])
    summary["area_total_m2"] = safe_numeric(summary["area_total_m2"])

    points["q_m3s"] = safe_numeric(points["q_m3s"])
    points["q_ls"] = safe_numeric(points["q_ls"])
    points["area_m2"] = safe_numeric(points["area_m2"])

    points_sum = (
        points.groupby(keys, dropna=False)
        .agg(
            q_points_m3s=("q_m3s", "sum"),
            q_points_ls=("q_ls", "sum"),
            area_points_m2=("area_m2", "sum"),
            n_points=("q_m3s", "count"),
        )
        .reset_index()
    )

    summary_sel = summary[
        keys + ["q_total_m3s", "q_total_ls", "area_total_m2"]
    ].copy()

    merged = summary_sel.merge(
        points_sum,
        on=keys,
        how="outer",
        indicator=True,
    )

    merged["q_diff_m3s"] = merged["q_points_m3s"] - merged["q_total_m3s"]
    merged["q_diff_ls"] = merged["q_points_ls"] - merged["q_total_ls"]

    merged["q_rel_diff_pct"] = (
        merged["q_diff_m3s"] / merged["q_total_m3s"] * 100
    )

    merged["area_diff_m2"] = merged["area_points_m2"] - merged["area_total_m2"]

    merged["area_rel_diff_pct"] = (
        merged["area_diff_m2"] / merged["area_total_m2"] * 100
    )

    merged["q_ok"] = merged["q_rel_diff_pct"].abs() <= q_tolerance_pct
    merged["area_ok"] = merged["area_rel_diff_pct"].abs() <= area_tolerance_pct

    merged["status"] = "ok"
    merged.loc[merged["_merge"] != "both", "status"] = "missing_pair"
    merged.loc[
        (merged["_merge"] == "both") & (~merged["q_ok"] | ~merged["area_ok"]),
        "status",
    ] = "inconsistent"

    path = write_report(merged, output_dir, "hydraulic_consistency_summary_points.csv")
    return path, merged