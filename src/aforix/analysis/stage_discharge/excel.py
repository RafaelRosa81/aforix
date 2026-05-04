from pathlib import Path

import pandas as pd


MAX_SHEET_NAME_LEN = 31


def write_excel_report(
    output_dir: Path,
    *,
    matched: pd.DataFrame,
    analysis_pairs: pd.DataFrame,
    fits: pd.DataFrame,
    metrics: pd.DataFrame,
    best_models: pd.DataFrame,
) -> Path:
    report_path = output_dir / "stage_discharge_report.xlsx"

    with pd.ExcelWriter(report_path, engine="openpyxl") as writer:
        _write_sheet(writer, "README", _readme_table(output_dir))
        _write_sheet(writer, "MatchedPairs", matched)
        _write_sheet(writer, "AnalysisPairs", analysis_pairs)
        _write_sheet(writer, "Fits", fits)
        _write_sheet(writer, "Metrics", metrics)
        _write_sheet(writer, "BestModels", best_models)

        for sheet_name, group_df in _iter_group_sheets(analysis_pairs):
            _write_sheet(writer, sheet_name, group_df)

    return report_path


def _write_sheet(writer: pd.ExcelWriter, sheet_name: str, df: pd.DataFrame) -> None:
    safe_name = _safe_sheet_name(sheet_name)
    df.to_excel(writer, sheet_name=safe_name, index=False)
    ws = writer.book[safe_name]
    ws.freeze_panes = "A2"
    for cell in ws[1]:
        cell.style = "Headline 3"
    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col[:200]:
            value = "" if cell.value is None else str(cell.value)
            max_len = max(max_len, len(value))
        ws.column_dimensions[col_letter].width = min(max(max_len + 2, 10), 40)


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
        "station_name",
        "measurement_date",
        "measurement_time",
        "analysis_group",
        "instrument",
        "rank",
        "q_total_ls",
        "q_total_m3s",
        "normalized_source_table",
        "original_source_file",
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
        return group_df.sort_values(["measurement_date", "instrument"])

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

    ordered_cols = available_base + ["stage_manual_m", "stage_mean_m", "stage_max_m"]
    wide = wide[ordered_cols]
    return wide.sort_values(["measurement_date", "instrument"]).reset_index(drop=True)


def _readme_table(output_dir: Path) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"item": "report", "value": "Stage-discharge analysis report"},
            {"item": "output_dir", "value": str(output_dir)},
            {"item": "source", "value": "database/normalized + database/external/normalized/manual_stage"},
            {"item": "group_sheets", "value": "One sheet per station_id + analysis_group. Each sheet combines manual, mean and max stage columns."},
            {"item": "stage_columns", "value": "stage_manual_m, stage_mean_m, stage_max_m"},
        ]
    )


def _safe_sheet_name(name: str) -> str:
    safe = str(name).replace("/", "-").replace("\\", "-").replace("*", "-").replace("?", "-").replace("[", "(").replace("]", ")")
    return safe[:MAX_SHEET_NAME_LEN]
