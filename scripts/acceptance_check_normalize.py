from __future__ import annotations

import argparse
import math
from pathlib import Path

import pandas as pd
import yaml


IDENTITY = [
    "instrument",
    "station_id",
    "measurement_date",
    "measurement_time",
    "source_file",
]


def project_root_from_config(config_path: Path) -> Path:
    resolved = config_path.resolve()
    for candidate in [resolved.parent, *resolved.parents]:
        if (candidate / ".git").exists() or (candidate / "pyproject.toml").exists():
            return candidate
    return Path.cwd().resolve()


def resolve_path(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str)


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def first_existing(df: pd.DataFrame, names: list[str]) -> pd.Series:
    valid = [name for name in names if name in df.columns]
    if not valid:
        return pd.Series([pd.NA] * len(df), index=df.index, dtype="object")
    out = df[valid[0]].copy()
    for name in valid[1:]:
        out = out.combine_first(df[name])
    return out


def _canonical_date(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    if not text:
        return ""
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 8:
        if len(digits) == 8:
            return digits
        if len(digits) >= 14:
            return digits[:8]
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        return text
    return parsed.strftime("%Y%m%d")


def _canonical_time(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if "T" in text or " " in text:
        parsed = pd.to_datetime(text, errors="coerce")
        if not pd.isna(parsed):
            return parsed.strftime("%H%M%S")
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) == 6:
        return digits
    parsed = pd.to_datetime(text, format="%H:%M:%S", errors="coerce")
    if pd.isna(parsed):
        parsed = pd.to_datetime(text, format="%H:%M", errors="coerce")
    if pd.isna(parsed):
        return text
    return parsed.strftime("%H%M%S")


def _canonical_index(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    if not text:
        return ""
    try:
        number = float(text)
        if number.is_integer():
            return str(int(number))
    except ValueError:
        pass
    return text


def _coalesce_identity_column(df: pd.DataFrame, aliases: list[str]) -> pd.Series:
    valid = [col for col in aliases if col in df.columns]
    if not valid:
        raise ValueError(f"missing identity columns: {aliases}")
    out = df[valid[0]].copy()
    for col in valid[1:]:
        out = out.combine_first(df[col])
    return out


def identity_frame(
    df: pd.DataFrame,
    *,
    extra_aliases: dict[str, list[str]] | None = None,
) -> pd.DataFrame:
    required = ["instrument", "station_id", "measurement_date", "measurement_time", "source_file"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"missing identity columns: {missing}")

    out = pd.DataFrame(index=df.index)
    out["instrument"] = df["instrument"].fillna("").astype(str).str.strip()
    out["station_id"] = df["station_id"].fillna("").astype(str).str.strip()
    out["measurement_date"] = df["measurement_date"].map(_canonical_date)
    out["measurement_time"] = df["measurement_time"].map(_canonical_time)
    out["source_file"] = df["source_file"].fillna("").astype(str).str.strip()

    for canonical, aliases in (extra_aliases or {}).items():
        out[canonical] = _coalesce_identity_column(df, aliases).map(_canonical_index)

    cols = list(out.columns)
    return out.sort_values(cols, kind="stable").reset_index(drop=True)


def compare_identity(
    expected: pd.DataFrame,
    observed: pd.DataFrame,
    *,
    extra_aliases: dict[str, list[str]] | None = None,
) -> tuple[bool, str]:
    try:
        exp = identity_frame(expected, extra_aliases=extra_aliases)
        obs = identity_frame(observed, extra_aliases=extra_aliases)
    except Exception as exc:
        return False, str(exc)

    if len(exp) != len(obs):
        return False, f"row count differs: expected={len(exp)} observed={len(obs)}"
    if not exp.equals(obs):
        bad = (exp != obs).any(axis=1)
        idx = int(bad[bad].index[0])
        return False, f"identity mismatch at sorted row {idx}: expected={exp.iloc[idx].to_dict()} observed={obs.iloc[idx].to_dict()}"
    return True, ""


def close_series(expected: pd.Series, observed: pd.Series, *, atol: float = 1e-9) -> tuple[int, float]:
    exp = numeric(expected)
    obs = numeric(observed)
    comparable = exp.notna() & obs.notna()
    missing_mismatch = exp.isna() ^ obs.isna()
    diff = (exp - obs).abs()
    bad = missing_mismatch | (comparable & (diff > atol))
    max_diff = float(diff[comparable].max()) if comparable.any() else 0.0
    return int(bad.sum()), max_diff


def load_file_group(root: Path, instrument: str, group: str) -> tuple[list[Path], pd.DataFrame]:
    group_dir = root / instrument / group
    paths = sorted(group_dir.glob("*.csv")) if group_dir.exists() else []
    frames = [read_csv(path) for path in paths]
    merged = pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()
    return paths, merged


def check_summary_source_fidelity(instrument: str, raw: pd.DataFrame, norm: pd.DataFrame) -> tuple[int, list[str]]:
    raw_sorted = raw.sort_values(IDENTITY, kind="stable").reset_index(drop=True)
    norm_sorted = norm.sort_values(IDENTITY, kind="stable").reset_index(drop=True)
    issues: list[str] = []
    mismatches = 0

    if instrument == "flowtracker":
        q_raw = first_existing(raw_sorted, ["total_discharge_m3_s", "total_discharge_m3s", "discharge_m3_s", "caudal_total_m3_s"])
        area_raw = first_existing(raw_sorted, ["total_area_m2", "area_total_m2", "area_m2"])
        vel_raw = first_existing(raw_sorted, ["mean_velocity_m_s", "velocidad_media_m_s", "mean_velocity_ms", "velocity_mean_m_s"])
        q_bad, _ = close_series(q_raw, norm_sorted["q_total_m3s"])
        area_bad, _ = close_series(area_raw, norm_sorted["area_total_m2"])
        vel_bad, _ = close_series(vel_raw, norm_sorted["velocity_mean_m_s"])
        mismatches += q_bad + area_bad + vel_bad
        if q_bad: issues.append(f"q_total_m3s mismatches={q_bad}")
        if area_bad: issues.append(f"area_total_m2 mismatches={area_bad}")
        if vel_bad: issues.append(f"velocity_mean_m_s mismatches={vel_bad}")

    elif instrument == "molinete":
        q_raw = first_existing(raw_sorted, ["q_total_m3s", "q_m3s", "total_discharge_m3s", "total_discharge_m3_s"])
        area_raw = first_existing(raw_sorted, ["area_total_m2", "area_m2", "total_area_m2"])
        vel_raw = first_existing(raw_sorted, ["velocity_mean_m_s", "vel_media_ms", "mean_velocity_ms"])
        q_bad, _ = close_series(q_raw, norm_sorted["q_total_m3s"])
        area_bad, _ = close_series(area_raw, norm_sorted["area_total_m2"])
        vel_bad, _ = close_series(vel_raw, norm_sorted["velocity_mean_m_s"])
        mismatches += q_bad + area_bad + vel_bad
        if q_bad: issues.append(f"q_total_m3s mismatches={q_bad}")
        if area_bad: issues.append(f"area_total_m2 mismatches={area_bad}")
        if vel_bad: issues.append(f"velocity_mean_m_s mismatches={vel_bad}")

    elif instrument == "nivus":
        q_ls_raw = first_existing(raw_sorted, ["q_total_ls", "total_discharge_ls", "q [l/s]"])
        area_raw = first_existing(raw_sorted, ["area_total_m2", "total_area_m2", "a [m²]"])
        vel_raw = first_existing(raw_sorted, ["velocity_mean_m_s", "mean_velocity_ms", "v_mean [m/s]"])
        q_bad, _ = close_series(q_ls_raw, norm_sorted["q_total_ls"])
        area_bad, _ = close_series(area_raw, norm_sorted["area_total_m2"])
        vel_bad, _ = close_series(vel_raw, norm_sorted["velocity_mean_m_s"])
        mismatches += q_bad + area_bad + vel_bad
        if q_bad: issues.append(f"q_total_ls mismatches={q_bad}")
        if area_bad: issues.append(f"area_total_m2 mismatches={area_bad}")
        if vel_bad: issues.append(f"velocity_mean_m_s mismatches={vel_bad}")

    return mismatches, issues


def main() -> None:
    parser = argparse.ArgumentParser(description="Real-data acceptance check for normalize.")
    parser.add_argument("--config", default="configs/examples/acceptance_real.yaml")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    root = project_root_from_config(config_path)
    with config_path.open("r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    normalize_cfg = cfg["normalize"]
    raw_root = resolve_path(root, normalize_cfg["input_dir"])
    norm_root = resolve_path(root, normalize_cfg["output_dir"])

    instruments = ["flowtracker", "molinete", "nivus"]
    report_rows: list[dict[str, object]] = []

    summary_total = 0
    points_total = 0

    for instrument in instruments:
        raw_summary_path = raw_root / instrument / "Summary.csv"
        norm_summary_path = norm_root / instrument / "Summary.csv"

        if not raw_summary_path.exists() or not norm_summary_path.exists():
            report_rows.append({
                "instrument": instrument,
                "group": "Summary",
                "status": "FAIL",
                "detail": "missing raw or normalized Summary.csv",
            })
        else:
            raw_summary = read_csv(raw_summary_path)
            norm_summary = read_csv(norm_summary_path)
            summary_total += len(norm_summary)
            identity_ok, identity_detail = compare_identity(raw_summary, norm_summary)
            fidelity_bad, fidelity_issues = check_summary_source_fidelity(instrument, raw_summary, norm_summary)

            unit_bad = 0
            if {"q_total_m3s", "q_total_ls"}.issubset(norm_summary.columns):
                expected_ls = numeric(norm_summary["q_total_m3s"]) * 1000.0
                unit_bad, _ = close_series(expected_ls, norm_summary["q_total_ls"], atol=1e-6)

            passed = (
                len(raw_summary) == len(norm_summary)
                and identity_ok
                and fidelity_bad == 0
                and unit_bad == 0
            )
            report_rows.append({
                "instrument": instrument,
                "group": "Summary",
                "raw_rows": len(raw_summary),
                "normalized_rows": len(norm_summary),
                "identity_ok": identity_ok,
                "source_numeric_mismatches": fidelity_bad,
                "unit_mismatches": unit_bad,
                "status": "PASS" if passed else "FAIL",
                "detail": " | ".join([identity_detail, *fidelity_issues]).strip(" |"),
            })

        raw_point_paths, raw_points = load_file_group(raw_root, instrument, "Points")
        norm_point_paths, norm_points = load_file_group(norm_root, instrument, "Points")
        points_total += len(norm_points)

        if raw_points.empty or norm_points.empty:
            report_rows.append({
                "instrument": instrument,
                "group": "Points",
                "status": "FAIL",
                "detail": "missing raw or normalized Points files",
            })
        else:
            point_aliases = {
                "flowtracker": ["point_index", "station"],
                "molinete": ["point_index", "index"],
                "nivus": ["point_index", "index"],
            }
            identity_ok, identity_detail = compare_identity(
                raw_points,
                norm_points,
                extra_aliases={"point_index": point_aliases[instrument]},
            )

            unit_bad = 0
            if {"q_m3s", "q_ls"}.issubset(norm_points.columns):
                expected_ls = numeric(norm_points["q_m3s"]) * 1000.0
                unit_bad, _ = close_series(expected_ls, norm_points["q_ls"], atol=1e-6)

            passed = (
                len(raw_point_paths) == len(norm_point_paths)
                and len(raw_points) == len(norm_points)
                and identity_ok
                and unit_bad == 0
            )
            report_rows.append({
                "instrument": instrument,
                "group": "Points",
                "raw_files": len(raw_point_paths),
                "normalized_files": len(norm_point_paths),
                "raw_rows": len(raw_points),
                "normalized_rows": len(norm_points),
                "identity_ok": identity_ok,
                "unit_mismatches": unit_bad,
                "status": "PASS" if passed else "FAIL",
                "detail": identity_detail,
            })

    for group in ("Sections", "Gates"):
        raw_paths, raw_df = load_file_group(raw_root, "nivus", group)
        norm_paths, norm_df = load_file_group(norm_root, "nivus", group)

        if group == "Sections":
            extra_aliases = {"section_index": ["section_index", "index"]}
        else:
            extra_aliases = {
                "point_index": ["point_index"],
                "gate_index": ["gate_index", "index"],
            }
        identity_ok, identity_detail = compare_identity(
            raw_df,
            norm_df,
            extra_aliases=extra_aliases,
        )

        unit_bad = 0
        if group == "Sections" and {"q_m3s", "q_ls"}.issubset(norm_df.columns):
            expected_ls = numeric(norm_df["q_m3s"]) * 1000.0
            unit_bad, _ = close_series(expected_ls, norm_df["q_ls"], atol=1e-6)

        passed = (
            len(raw_paths) == len(norm_paths)
            and len(raw_df) == len(norm_df)
            and identity_ok
            and unit_bad == 0
        )
        report_rows.append({
            "instrument": "nivus",
            "group": group,
            "raw_files": len(raw_paths),
            "normalized_files": len(norm_paths),
            "raw_rows": len(raw_df),
            "normalized_rows": len(norm_df),
            "identity_ok": identity_ok,
            "unit_mismatches": unit_bad,
            "status": "PASS" if passed else "FAIL",
            "detail": identity_detail,
        })

    cross_summary_path = norm_root / "Summary.csv"
    cross_points_path = norm_root / "Points.csv"

    cross_summary_rows = len(read_csv(cross_summary_path)) if cross_summary_path.exists() else -1
    cross_points_rows = len(read_csv(cross_points_path)) if cross_points_path.exists() else -1

    cross_summary_ok = cross_summary_rows == summary_total
    cross_points_ok = cross_points_rows == points_total

    report_rows.append({
        "instrument": "all",
        "group": "Summary_concat",
        "normalized_rows": cross_summary_rows,
        "expected_rows": summary_total,
        "status": "PASS" if cross_summary_ok else "FAIL",
        "detail": "",
    })
    report_rows.append({
        "instrument": "all",
        "group": "Points_concat",
        "normalized_rows": cross_points_rows,
        "expected_rows": points_total,
        "status": "PASS" if cross_points_ok else "FAIL",
        "detail": "",
    })

    report = pd.DataFrame(report_rows)
    runs_root = resolve_path(root, cfg["paths"].get("runs_root", "runs"))
    checks_dir = runs_root / "_checks"
    checks_dir.mkdir(parents=True, exist_ok=True)
    report_path = checks_dir / "normalize_acceptance.csv"
    report.to_csv(report_path, index=False, encoding="utf-8-sig")

    n_pass = int((report["status"] == "PASS").sum())
    n_fail = int((report["status"] == "FAIL").sum())

    print("Aforix normalize real-data acceptance")
    print("=" * 37)
    print(f"Checks: {len(report)}")
    print(f"PASS: {n_pass}")
    print(f"FAIL: {n_fail}")
    print(f"Cross-instrument Summary rows: {cross_summary_rows}")
    print(f"Cross-instrument Points rows : {cross_points_rows}")
    print(f"Report: {report_path}")

    if n_fail:
        print("")
        print("Failed checks:")
        cols = [
            "instrument",
            "group",
            "raw_rows",
            "normalized_rows",
            "identity_ok",
            "source_numeric_mismatches",
            "unit_mismatches",
            "detail",
        ]
        for col in cols:
            if col not in report.columns:
                report[col] = pd.NA
        print(report.loc[report["status"] == "FAIL", cols].to_string(index=False))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
