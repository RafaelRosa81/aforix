from pathlib import Path
from typing import Any

import pandas as pd


MAX_SHEET_NAME_LEN = 31
DROP_COLUMNS = ["station_name", "original_source_file", "source_run_dir"]
TRACEABILITY_COLUMNS = ["normalized_source_table", "run_id"]
METRIC_RENAMES = {
    "rmse": "rmse_ls",
    "mae": "mae_ls",
    "bias": "bias_ls",
    "nrmse": "nrmse_ratio",
    "pbias_pct": "pbias_pct",
    "r2": "r2_dimensionless",
    "nse": "nse_dimensionless",
}


def write_excel_report(
    output_dir: Path,
    *,
    matched: pd.DataFrame,
    analysis_pairs: pd.DataFrame,
    fits: pd.DataFrame,
    metrics: pd.DataFrame,
    best_models: pd.DataFrame,
    config: dict[str, Any] | None = None,
) -> Path:
    report_path = output_dir / "stage_discharge_report.xlsx"

    with pd.ExcelWriter(report_path, engine="openpyxl") as writer:
        _write_sheet(writer, "README", _readme_table(output_dir, config or {}))
        _write_sheet(writer, "AnalysisPairs", _prepare_general_sheet(analysis_pairs))
        _write_fits_sheet(writer, fits)
        _write_sheet(writer, "Metrics", _prepare_metrics_sheet(metrics))
        _write_sheet(writer, "BestModels", _prepare_metrics_sheet(best_models))

        for sheet_name, group_df in _iter_group_sheets(analysis_pairs):
            _write_sheet(writer, sheet_name, group_df)

    return report_path


def _write_sheet(writer: pd.ExcelWriter, sheet_name: str, df: pd.DataFrame) -> None:
    safe_name = _safe_sheet_name(sheet_name)
    df.to_excel(writer, sheet_name=safe_name, index=False)
    _format_worksheet(writer, safe_name, header_row=1)


def _write_fits_sheet(writer: pd.ExcelWriter, fits: pd.DataFrame) -> None:
    safe_name = "Fits"
    guide = _fits_guide_table()
    guide.to_excel(writer, sheet_name=safe_name, index=False, startrow=0)
    start_row = len(guide) + 3
    _prepare_general_sheet(fits).to_excel(writer, sheet_name=safe_name, index=False, startrow=start_row)
    _format_worksheet(writer, safe_name, header_row=1)
    _format_worksheet(writer, safe_name, header_row=start_row + 1)
    ws = writer.book[safe_name]
    ws.freeze_panes = f"A{start_row + 2}"


def _format_worksheet(writer: pd.ExcelWriter, sheet_name: str, header_row: int) -> None:
    ws = writer.book[sheet_name]
    for cell in ws[header_row]:
        cell.style = "Headline 3"
    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col[:250]:
            value = "" if cell.value is None else str(cell.value)
            max_len = max(max_len, len(value))
        ws.column_dimensions[col_letter].width = min(max(max_len + 2, 10), 42)


def _iter_group_sheets(analysis_pairs: pd.DataFrame):
    if analysis_pairs.empty:
        return
    group_cols = ["station_id", "analysis_group"]
    for keys, group_df in analysis_pairs.groupby(group_cols):
        station_id, analysis_group = keys
        sheet_name = f"{station_id}_{analysis_group}"
        yield sheet_name, _wide_group_table(group_df)


def _wide_group_table(group_df: pd.DataFrame) -> pd.DataFrame:
    base_cols = [
        "station_id",
        "measurement_date",
        "measurement_time",
        "analysis_group",
        "instrument",
        "rank",
        "q_total_ls",
        "q_total_m3s",
        "normalized_source_table",
        "run_id",
    ]
    available_base = [c for c in base_cols if c in group_df.columns]

    pivot_index = available_base
    tmp = group_df.copy()
    tmp["stage_column"] = tmp["stage_type"].map(
        {
            "manual": "stage_manual_m",
            "mean": "stage_mean_m",
            "max": "stage_max_m",
        }
    )

    tmp = tmp.dropna(subset=["stage_column"])
    if tmp.empty:
        return _prepare_general_sheet(group_df.sort_values(["measurement_date", "instrument"]))

    wide = (
        tmp.pivot_table(
            index=pivot_index,
            columns="stage_column",
            values="stage_m",
            aggfunc="first",
        )
        .reset_index()
    )
    wide.columns.name = None

    for col in ["stage_manual_m", "stage_mean_m", "stage_max_m"]:
        if col not in wide.columns:
            wide[col] = pd.NA

    ordered_cols = [
        "station_id",
        "measurement_date",
        "measurement_time",
        "analysis_group",
        "instrument",
        "rank",
        "q_total_ls",
        "q_total_m3s",
        "stage_manual_m",
        "stage_mean_m",
        "stage_max_m",
        "normalized_source_table",
        "run_id",
    ]
    ordered_cols = [c for c in ordered_cols if c in wide.columns]
    wide = wide[ordered_cols]
    return wide.sort_values(["measurement_date", "instrument"]).reset_index(drop=True)


def _fits_guide_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"model": "poly1", "generic_equation": "Q = a·H + b", "coefficients": "a, b"},
            {"model": "poly2", "generic_equation": "Q = a·H² + b·H + c", "coefficients": "a, b, c"},
            {"model": "power", "generic_equation": "Q = a·H^b", "coefficients": "a, b"},
            {"model": "variables", "generic_equation": "Q is discharge in L/s; H is stage/depth in m", "coefficients": ""},
        ]
    )


def _prepare_general_sheet(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out = out.drop(columns=[c for c in DROP_COLUMNS if c in out.columns], errors="ignore")
    return _move_traceability_right(out)


def _prepare_metrics_sheet(df: pd.DataFrame) -> pd.DataFrame:
    out = _prepare_general_sheet(df)
    out = out.rename(columns={k: v for k, v in METRIC_RENAMES.items() if k in out.columns})
    return _move_traceability_right(out)


def _move_traceability_right(df: pd.DataFrame) -> pd.DataFrame:
    cols = list(df.columns)
    trace = [c for c in TRACEABILITY_COLUMNS if c in cols]
    non_trace = [c for c in cols if c not in trace]
    return df[non_trace + trace]


def _readme_table(output_dir: Path, config: dict[str, Any]) -> pd.DataFrame:
    rows = [
        {"item": "report", "value": "Stage-discharge analysis report"},
        {"item": "output_dir", "value": str(output_dir)},
        {"item": "source", "value": "database/normalized + database/external/normalized/manual_stage"},
        {"item": "group_sheets", "value": "One sheet per station_id + analysis_group. Each sheet combines manual, mean and max stage columns."},
        {"item": "stage_columns", "value": "stage_manual_m, stage_mean_m, stage_max_m"},
        {"item": "fit_equations", "value": "See Fits sheet for generic equations and coefficient interpretation."},
        {"item": "metric_units", "value": "q_total_ls, rmse_ls, mae_ls and bias_ls are in L/s; q_total_m3s is in m3/s; stage_* columns are in m."},
    ]
    rows.extend(_flatten_config(config, prefix="config"))
    return pd.DataFrame(rows)


def _flatten_config(value: Any, *, prefix: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            rows.extend(_flatten_config(item, prefix=f"{prefix}.{key}"))
    elif isinstance(value, list):
        rows.append({"item": prefix, "value": ", ".join(str(v) for v in value)})
    else:
        rows.append({"item": prefix, "value": str(value)})
    return rows


def _safe_sheet_name(name: str) -> str:
    safe = str(name).replace("/", "-").replace("\\", "-").replace("*", "-").replace("?", "-").replace("[", "(").replace("]", ")")
    return safe[:MAX_SHEET_NAME_LEN]
