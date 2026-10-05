from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook


def _norm_date(value: object) -> str:
    text = str(value).strip()
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    compact = "".join(ch for ch in text if ch.isdigit())[:8]
    if len(compact) == 8:
        return f"{compact[:4]}-{compact[4:6]}-{compact[6:8]}"
    return text


def _latest_workbook(root: Path) -> Path:
    candidates = sorted(
        root.glob("*/*.xlsx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise SystemExit(f"No section-profile workbook found under {root}")
    return candidates[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--station", required=True)
    parser.add_argument("--instrument", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument(
        "--root",
        default="runs_acceptance/analysis_section_profiles",
    )
    args = parser.parse_args()

    root = Path(args.root)
    workbook = _latest_workbook(root)

    xls = pd.ExcelFile(workbook)
    checks: list[dict[str, str]] = []

    has_readme = "README" in xls.sheet_names
    has_index = "Index" in xls.sheet_names
    checks.append({
        "check": "workbook_structure",
        "status": "PASS" if has_readme and has_index else "FAIL",
        "detail": f"README={has_readme}, Index={has_index}, sheets={len(xls.sheet_names)}",
    })

    if not has_index:
        report = pd.DataFrame(checks)
        print(report.to_string(index=False))
        raise SystemExit(1)

    index = pd.read_excel(workbook, sheet_name="Index", dtype=str).fillna("")
    target_date = _norm_date(args.date)

    identity_ok = (
        not index.empty
        and set(index["station_id"]) == {str(args.station)}
        and set(index["instrument"]) == {str(args.instrument)}
        and set(index["measurement_date"].map(_norm_date)) == {target_date}
    )
    checks.append({
        "check": "authoritative_identity",
        "status": "PASS" if identity_ok else "FAIL",
        "detail": (
            f"rows={len(index)}, stations={sorted(set(index.get('station_id', [])))}, "
            f"instruments={sorted(set(index.get('instrument', [])))}, "
            f"dates={sorted(set(index.get('measurement_date', pd.Series(dtype=str)).map(_norm_date)))}"
        ),
    })

    no_p_alias = not index["station_id"].str.match(r"(?i)^p\d+$").any()
    checks.append({
        "check": "no_legacy_p_alias",
        "status": "PASS" if no_p_alias else "FAIL",
        "detail": f"station_ids={sorted(set(index['station_id']))}",
    })

    n_rows_ok = True
    n_rows_details: list[str] = []
    for _, row in index.iterrows():
        try:
            n_rows = int(float(row["n_rows"]))
        except Exception:
            n_rows = -1
        sheet = str(row["sheet_name"])
        if sheet not in xls.sheet_names or n_rows <= 0:
            n_rows_ok = False
            n_rows_details.append(f"{sheet}: invalid n_rows={row.get('n_rows')}")
            continue

        data = pd.read_excel(
            workbook,
            sheet_name=sheet,
            skiprows=12,
        )
        # The writer places 9 summary rows, one blank row, then the tabular header.
        # If layout changes, fall back to locating distance/depth columns manually.
        if "distance_m" not in data.columns or "depth_m" not in data.columns:
            raw = pd.read_excel(workbook, sheet_name=sheet, header=None)
            header_idx = None
            for i in range(len(raw)):
                vals = {str(v) for v in raw.iloc[i].dropna().tolist()}
                if {"distance_m", "depth_m"}.issubset(vals):
                    header_idx = i
                    break
            if header_idx is None:
                n_rows_ok = False
                n_rows_details.append(f"{sheet}: data header not found")
                continue
            data = pd.read_excel(workbook, sheet_name=sheet, skiprows=header_idx)

        actual_rows = len(data.dropna(how="all"))
        if actual_rows != n_rows:
            n_rows_ok = False
        n_rows_details.append(f"{sheet}: index={n_rows}, data={actual_rows}")

    checks.append({
        "check": "data_row_counts",
        "status": "PASS" if n_rows_ok else "FAIL",
        "detail": "; ".join(n_rows_details),
    })

    wb = load_workbook(workbook, read_only=False, data_only=False)
    chart_ok = True
    chart_details: list[str] = []
    for sheet in index["sheet_name"]:
        if sheet not in wb.sheetnames:
            chart_ok = False
            chart_details.append(f"{sheet}: missing")
            continue
        n_charts = len(wb[sheet]._charts)
        if n_charts != 1:
            chart_ok = False
        chart_details.append(f"{sheet}: charts={n_charts}")

    checks.append({
        "check": "one_chart_per_measurement",
        "status": "PASS" if chart_ok else "FAIL",
        "detail": "; ".join(chart_details),
    })

    report = pd.DataFrame(checks)
    report_dir = Path("runs_acceptance/_checks")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "section_profiles_acceptance.csv"
    report.to_csv(report_path, index=False, encoding="utf-8-sig")

    n_pass = int(report["status"].eq("PASS").sum())
    n_fail = int(report["status"].eq("FAIL").sum())

    print("Aforix section profiles acceptance")
    print("=================================")
    print(f"Workbook: {workbook}")
    print(f"Checks: {len(report)}")
    print(f"PASS: {n_pass}")
    print(f"FAIL: {n_fail}")
    print(f"Report: {report_path}")
    print("")
    print(report.to_string(index=False))

    if n_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
