from pathlib import Path
import pandas as pd


SUMMARY_FILE = Path("database/normalized/Summary.csv")
POINTS_FILE = Path("database/normalized/Points.csv")
OUT_FILE = Path("database/validation/hydraulic_consistency_summary_points.csv")

KEYS = ["instrument", "station_id", "measurement_date", "measurement_time"]


def _safe_numeric(series):
    return pd.to_numeric(series, errors="coerce")


def main():
    print("Loading normalized datasets...")

    summary = pd.read_csv(SUMMARY_FILE, dtype=str)
    points = pd.read_csv(POINTS_FILE, dtype=str)

    summary["q_total_m3s"] = _safe_numeric(summary["q_total_m3s"])
    summary["q_total_ls"] = _safe_numeric(summary["q_total_ls"])
    summary["area_total_m2"] = _safe_numeric(summary["area_total_m2"])

    points["q_m3s"] = _safe_numeric(points["q_m3s"])
    points["q_ls"] = _safe_numeric(points["q_ls"])
    points["area_m2"] = _safe_numeric(points["area_m2"])

    print("Aggregating points...")

    points_sum = (
        points
        .groupby(KEYS, dropna=False)
        .agg(
            q_points_m3s=("q_m3s", "sum"),
            q_points_ls=("q_ls", "sum"),
            area_points_m2=("area_m2", "sum"),
            n_points=("q_m3s", "count"),
        )
        .reset_index()
    )

    summary_sel = summary[
        KEYS + ["q_total_m3s", "q_total_ls", "area_total_m2"]
    ].copy()

    print("Merging summary and points...")

    merged = summary_sel.merge(
        points_sum,
        on=KEYS,
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

    merged["q_ok_1pct"] = merged["q_rel_diff_pct"].abs() <= 1.0
    merged["area_ok_1pct"] = merged["area_rel_diff_pct"].abs() <= 1.0

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUT_FILE, index=False)

    print("\n=== Hydraulic consistency: Summary vs Points ===")
    print(
        merged[
            [
                "instrument",
                "station_id",
                "measurement_date",
                "measurement_time",
                "q_total_m3s",
                "q_points_m3s",
                "q_diff_m3s",
                "q_rel_diff_pct",
                "area_total_m2",
                "area_points_m2",
                "area_diff_m2",
                "area_rel_diff_pct",
                "n_points",
                "_merge",
            ]
        ].to_string(index=False)
    )

    print("\nSaved:", OUT_FILE)

    print("\n=== Counts by instrument ===")
    print(
        merged.groupby("instrument")[["q_ok_1pct", "area_ok_1pct"]]
        .sum()
        .fillna(0)
    )


if __name__ == "__main__":
    main()