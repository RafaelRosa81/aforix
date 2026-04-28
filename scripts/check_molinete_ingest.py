from pathlib import Path
import argparse
import pandas as pd
import numpy as np


def rel_diff(a, b):
    if pd.isna(a) or pd.isna(b):
        return np.nan
    if abs(a) < 1e-12:
        return abs(b - a)
    return abs(b - a) / abs(a) * 100


def to_float(value):
    try:
        return float(value)
    except Exception:
        return np.nan


def build_key_from_file(path: Path):
    # Expected: P11_Summary_20260119_141800.csv
    parts = path.stem.split("_")
    if len(parts) < 4:
        return None
    station_id = parts[0]
    group = parts[1]
    date = parts[2]
    time = parts[3]
    return station_id, date, time


def check_pair(summary_file: Path, points_file: Path) -> dict:
    summary = pd.read_csv(summary_file)
    points = pd.read_csv(points_file)

    s = summary.iloc[0]

    station_id = s.get("station_id")
    measurement_date = s.get("measurement_date")
    measurement_time = s.get("measurement_time")

    n_points_summary = to_float(s.get("n_points"))
    n_points_points = len(points)

    q_summary = to_float(s.get("q_m3s"))
    q_points_sum = points["q_m3s"].sum() if "q_m3s" in points else np.nan

    area_summary = to_float(s.get("area_m2"))
    area_points_sum = points["area_m2"].sum() if "area_m2" in points else np.nan

    vel_summary = to_float(s.get("vel_media_ms"))
    vel_calc = q_summary / area_summary if area_summary and not pd.isna(area_summary) else np.nan

    prof_media_summary = to_float(s.get("prof_media_m"))
    prof_media_calc = points["prof_m"].mean() if "prof_m" in points else np.nan

    ancho_summary = to_float(s.get("ancho_m"))
    if "progr_m" in points and len(points["progr_m"].dropna()) >= 2:
        progr = points["progr_m"].dropna().sort_values().to_list()
        ancho_calc = progr[-1] + 0.5 * (progr[-1] - progr[-2])
    else:
        ancho_calc = np.nan

    q_percent_sum = points["q_percent"].sum() if "q_percent" in points else np.nan

    warnings = []

    q_diff_pct = rel_diff(q_summary, q_points_sum)
    area_diff_pct = rel_diff(area_summary, area_points_sum)
    vel_diff_abs = abs(vel_summary - vel_calc) if not pd.isna(vel_summary) and not pd.isna(vel_calc) else np.nan
    prof_media_diff_abs = abs(prof_media_summary - prof_media_calc) if not pd.isna(prof_media_summary) and not pd.isna(prof_media_calc) else np.nan
    ancho_diff_abs = abs(ancho_summary - ancho_calc) if not pd.isna(ancho_summary) and not pd.isna(ancho_calc) else np.nan

    if n_points_summary != n_points_points:
        warnings.append("n_points mismatch")

    if not pd.isna(q_diff_pct) and q_diff_pct > 1:
        warnings.append("q_m3s Summary != sum Points q_m3s")

    if not pd.isna(area_diff_pct) and area_diff_pct > 1:
        warnings.append("area_m2 Summary != sum Points area_m2")

    if not pd.isna(vel_diff_abs) and vel_diff_abs > 0.01:
        warnings.append("vel_media_ms != q_m3s/area_m2")

    if not pd.isna(prof_media_diff_abs) and prof_media_diff_abs > 0.001:
        warnings.append("prof_media_m mismatch")

    if not pd.isna(ancho_diff_abs) and ancho_diff_abs > 0.001:
        warnings.append("ancho_m mismatch")

    if not pd.isna(q_percent_sum) and not (99 <= q_percent_sum <= 101):
        warnings.append("q_percent sum not near 100")

    if "progr_m" in points and points["progr_m"].isna().any():
        warnings.append("empty progr_m")

    if "prof_m" in points and points["prof_m"].isna().any():
        warnings.append("empty prof_m")

    if "q_m3s" in points and (points["q_m3s"] < 0).any():
        warnings.append("negative q_m3s")

    if "area_m2" in points and (points["area_m2"] < 0).any():
        warnings.append("negative area_m2")

    status = "OK" if not warnings else "CHECK"

    return {
        "station_id": station_id,
        "measurement_date": measurement_date,
        "measurement_time": measurement_time,
        "summary_file": summary_file.name,
        "points_file": points_file.name,
        "status": status,
        "warnings": " | ".join(warnings),

        "n_points_summary": n_points_summary,
        "n_points_points": n_points_points,

        "q_summary": q_summary,
        "q_points_sum": q_points_sum,
        "q_diff_abs": abs(q_summary - q_points_sum) if not pd.isna(q_summary) and not pd.isna(q_points_sum) else np.nan,
        "q_diff_pct": q_diff_pct,

        "area_summary": area_summary,
        "area_points_sum": area_points_sum,
        "area_diff_abs": abs(area_summary - area_points_sum) if not pd.isna(area_summary) and not pd.isna(area_points_sum) else np.nan,
        "area_diff_pct": area_diff_pct,

        "vel_summary": vel_summary,
        "vel_calc": vel_calc,
        "vel_diff_abs": vel_diff_abs,

        "prof_media_summary": prof_media_summary,
        "prof_media_calc": prof_media_calc,
        "prof_media_diff_abs": prof_media_diff_abs,

        "ancho_summary": ancho_summary,
        "ancho_calc": ancho_calc,
        "ancho_diff_abs": ancho_diff_abs,

        "q_percent_sum": q_percent_sum,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, help="Path to runs/ingest_molinete/<run_id>")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)

    base = run_dir / "outputs" / "raw_canonical" / "molinete"
    summary_dir = base / "Summary"
    points_dir = base / "Points"

    if not summary_dir.exists():
        raise FileNotFoundError(f"Summary directory not found: {summary_dir}")
    if not points_dir.exists():
        raise FileNotFoundError(f"Points directory not found: {points_dir}")

    summary_files = list(summary_dir.glob("*_Summary_*.csv"))
    points_files = list(points_dir.glob("*_Points_*.csv"))

    points_by_key = {}
    for p in points_files:
        key = build_key_from_file(p)
        if key:
            points_by_key[(key[0], key[1], key[2])] = p

    rows = []

    for sfile in summary_files:
        key = build_key_from_file(sfile)
        if not key:
            rows.append({
                "summary_file": sfile.name,
                "status": "CHECK",
                "warnings": "Could not parse Summary filename",
            })
            continue

        station_id, date, time = key
        pfile = points_by_key.get((station_id, date, time))

        if pfile is None:
            rows.append({
                "station_id": station_id,
                "measurement_date": date,
                "measurement_time": time,
                "summary_file": sfile.name,
                "points_file": None,
                "status": "CHECK",
                "warnings": "Missing Points file",
            })
            continue

        rows.append(check_pair(sfile, pfile))

    report = pd.DataFrame(rows)

    outpath = run_dir / "molinete_qc_report.csv"
    report.to_csv(outpath, index=False)

    print(f"QC report saved: {outpath}")

    if "status" in report.columns:
        print(report["status"].value_counts(dropna=False).to_string())

    if "warnings" in report.columns:
        problems = report[report["status"] != "OK"]
        if not problems.empty:
            print("\nFiles to check:")
            print(problems[["station_id", "measurement_date", "measurement_time", "warnings"]].to_string(index=False))


if __name__ == "__main__":
    main()