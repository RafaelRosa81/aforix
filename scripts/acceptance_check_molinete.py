from __future__ import annotations

import argparse
import math
import re
import unicodedata
from pathlib import Path

import pandas as pd
import yaml


def norm_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.strip().lower().replace(":", "")
    return re.sub(r"\s+", " ", text)


def numeric(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", ".")
    if not text or text == "-":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def clean_station(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).strip()
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", text).strip("_")
    return cleaned.upper()


def find_label(df: pd.DataFrame, label: str) -> tuple[int, int] | None:
    target = norm_text(label)
    for r in range(len(df)):
        for c in range(df.shape[1]):
            if target in norm_text(df.iat[r, c]):
                return r, c
    return None


def value_right_of(df: pd.DataFrame, label: str, max_scan: int = 8):
    pos = find_label(df, label)
    if pos is None:
        return None
    r, c = pos
    for cc in range(c + 1, min(c + 1 + max_scan, df.shape[1])):
        value = df.iat[r, cc]
        if not pd.isna(value) and str(value).strip() != "":
            return value
    return None


def read_raw_totals(path: Path, sheet_name: str) -> dict[str, object]:
    # Independent acceptance read: do not use aforix.ingest.adapters.molinete_excel.
    df = pd.read_excel(path, sheet_name=sheet_name, header=None, engine="xlrd")

    station_raw = value_right_of(df, "ESTACION")
    totals_pos = find_label(df, "TOTALES")
    if totals_pos is None:
        raise ValueError("TOTALES row not found")

    r, _ = totals_pos
    return {
        "raw_station_id": clean_station(station_raw),
        "raw_velocity_m_s": numeric(df.iat[r, 10]) if df.shape[1] > 10 else None,
        "raw_area_m2": numeric(df.iat[r, 11]) if df.shape[1] > 11 else None,
        "raw_q_m3s": numeric(df.iat[r, 12]) if df.shape[1] > 12 else None,
    }


def resolve_project_root(config_path: Path) -> Path:
    resolved = config_path.resolve()
    for candidate in [resolved.parent, *resolved.parents]:
        if (candidate / "pyproject.toml").exists() or (candidate / ".git").exists():
            return candidate
    return Path.cwd().resolve()


def latest_run(runs_root: Path) -> Path:
    root = runs_root / "ingest_molinete"
    candidates = sorted(p for p in root.iterdir() if p.is_dir())
    if not candidates:
        raise FileNotFoundError(f"No Molinete acceptance runs found in: {root}")
    return candidates[-1]


def same_number(a: object, b: object, tol: float) -> bool:
    aa = numeric(a)
    bb = numeric(b)
    if aa is None or bb is None:
        return aa is None and bb is None
    return math.isclose(aa, bb, rel_tol=0.0, abs_tol=tol)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Independent real-data acceptance check for Molinete ingest."
    )
    parser.add_argument(
        "--config",
        default="configs/examples/acceptance_real.yaml",
    )
    parser.add_argument("--run-dir", default=None)
    parser.add_argument("--tolerance", type=float, default=1e-9)
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    project_root = resolve_project_root(config_path)

    with config_path.open("r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    raw_root = project_root / cfg["paths"]["raw_data_dir"] / cfg["ingest"]["molinete"]["raw_subdir"]
    runs_root_value = Path(cfg["paths"].get("runs_root", "runs"))
    runs_root = runs_root_value if runs_root_value.is_absolute() else project_root / runs_root_value
    run_dir = Path(args.run_dir).resolve() if args.run_dir else latest_run(runs_root)

    summary_dir = run_dir / "outputs" / "raw_canonical" / "molinete" / "Summary"
    points_dir = run_dir / "outputs" / "raw_canonical" / "molinete" / "Points"

    summary_files = sorted(summary_dir.glob("*.csv"))
    point_files = sorted(points_dir.glob("*.csv"))

    rows: list[dict[str, object]] = []

    for summary_path in summary_files:
        summary = pd.read_csv(summary_path, dtype=str)
        if len(summary) != 1:
            rows.append({
                "summary_file": summary_path.name,
                "status": "FAIL",
                "detail": f"Summary has {len(summary)} rows instead of 1",
            })
            continue

        s = summary.iloc[0]
        source_file = str(s.get("source_file", "")).strip()
        raw_source_file = str(s.get("raw_source_file", "")).strip()

        source_path = Path(source_file) if source_file else raw_root / raw_source_file
        if not source_path.exists():
            source_path = raw_root / raw_source_file

        point_name = summary_path.name.replace("_Summary_", "_Points_")
        point_path = points_dir / point_name
        points = pd.read_csv(point_path, dtype=str) if point_path.exists() else pd.DataFrame()

        try:
            raw = read_raw_totals(source_path, cfg["ingest"]["molinete"].get("sheet_name", "CALCULO"))
        except Exception as exc:
            rows.append({
                "summary_file": summary_path.name,
                "raw_file": source_path.name,
                "status": "FAIL",
                "detail": f"RAW independent read failed: {exc}",
            })
            continue

        q_ok = same_number(raw["raw_q_m3s"], s.get("q_m3s"), args.tolerance)
        area_ok = same_number(raw["raw_area_m2"], s.get("area_m2"), args.tolerance)
        velocity_ok = same_number(raw["raw_velocity_m_s"], s.get("vel_media_ms"), args.tolerance)
        station_ok = str(raw["raw_station_id"]) == str(s.get("station_id", "")).strip()

        points_q = pd.to_numeric(points.get("q_m3s"), errors="coerce").sum(min_count=1) if not points.empty else math.nan
        points_area = pd.to_numeric(points.get("area_m2"), errors="coerce").sum(min_count=1) if not points.empty else math.nan
        points_q_ok = same_number(raw["raw_q_m3s"], points_q, 1e-6)
        points_area_ok = same_number(raw["raw_area_m2"], points_area, 1e-6)

        n_points_summary = numeric(s.get("n_points"))
        n_points_ok = (
            n_points_summary is not None
            and int(round(n_points_summary)) == len(points)
        )

        checks = {
            "station_ok": station_ok,
            "summary_q_ok": q_ok,
            "summary_area_ok": area_ok,
            "summary_velocity_ok": velocity_ok,
            "points_q_sum_ok": points_q_ok,
            "points_area_sum_ok": points_area_ok,
            "n_points_ok": n_points_ok,
        }
        passed = all(checks.values())

        rows.append({
            "raw_file": source_path.name,
            "summary_file": summary_path.name,
            "points_file": point_path.name,
            "station_id_raw": raw["raw_station_id"],
            "station_id_output": s.get("station_id"),
            "q_raw_m3s": raw["raw_q_m3s"],
            "q_summary_m3s": numeric(s.get("q_m3s")),
            "q_points_sum_m3s": numeric(points_q),
            "area_raw_m2": raw["raw_area_m2"],
            "area_summary_m2": numeric(s.get("area_m2")),
            "area_points_sum_m2": numeric(points_area),
            "velocity_raw_m_s": raw["raw_velocity_m_s"],
            "velocity_summary_m_s": numeric(s.get("vel_media_ms")),
            "n_points_summary": n_points_summary,
            "n_points_file": len(points),
            **checks,
            "status": "PASS" if passed else "FAIL",
            "detail": "",
        })

    result = pd.DataFrame(rows)
    outdir = runs_root / "_checks"
    outdir.mkdir(parents=True, exist_ok=True)
    outpath = outdir / "molinete_ingest_acceptance.csv"
    result.to_csv(outpath, index=False, encoding="utf-8-sig")

    n_pass = int((result["status"] == "PASS").sum()) if not result.empty else 0
    n_fail = int((result["status"] == "FAIL").sum()) if not result.empty else 0

    print("Aforix Molinete real-data acceptance")
    print("=" * 39)
    print(f"Run: {run_dir}")
    print(f"Summary files: {len(summary_files)}")
    print(f"Points files: {len(point_files)}")
    print(f"Measurements checked: {len(result)}")
    print(f"PASS: {n_pass}")
    print(f"FAIL: {n_fail}")
    print(f"Report: {outpath}")

    if n_fail:
        print("")
        print("Failed measurements:")
        cols = [
            "raw_file",
            "station_ok",
            "summary_q_ok",
            "summary_area_ok",
            "summary_velocity_ok",
            "points_q_sum_ok",
            "points_area_sum_ok",
            "n_points_ok",
        ]
        print(result.loc[result["status"] == "FAIL", cols].to_string(index=False))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
