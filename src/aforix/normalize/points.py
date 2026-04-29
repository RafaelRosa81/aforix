from pathlib import Path
import pandas as pd

from aforix.config.loader import load_config
from aforix.runs.manager import create_run


CANONICAL_COLUMNS = [
    "instrument",
    "station_id",
    "measurement_date",
    "measurement_time",
    "point_index",
    "point_label",
    "distance_m",
    "depth_m",
    "velocity_mean_m_s",
    "area_m2",
    "q_m3s",
    "q_ls",
    "percent_q",
    "temperature_c",
    "source_csv",
    "source_run_dir",
]


def _to_numeric(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def _empty_series(df: pd.DataFrame) -> pd.Series:
    return pd.Series([pd.NA] * len(df), index=df.index)


def _coalesce(df: pd.DataFrame, cols: list[str]) -> pd.Series:
    valid = [c for c in cols if c in df.columns]

    if not valid:
        return _empty_series(df)

    out = df[valid[0]].copy()

    for c in valid[1:]:
        out = out.combine_first(df[c])

    return out


def _format_date_yyyymmdd(series: pd.Series) -> pd.Series:
    s = series.astype("string").str.strip()
    s = s.str.replace("-", "", regex=False)
    s = s.str.replace("/", "", regex=False)
    s = s.str.replace(r"\.0$", "", regex=True)
    return s


def _format_time_hhmmss(series: pd.Series) -> pd.Series:
    s = series.astype("string").str.strip()
    s = s.str.replace(":", "", regex=False)
    s = s.str.replace(r"\.0$", "", regex=True)
    return s.str.zfill(6)


def _enrich_nivus_from_sections(
    out: pd.DataFrame,
    sections_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Enrich normalized Nivus Points using Nivus Sections.

    Rule:
    - first point receives first two sections
    - last point receives last two sections
    - middle points receive one section each

    Expected relation:
    len(sections) == len(points) + 2
    """

    if sections_df is None or sections_df.empty:
        print("WARNING: Nivus sections file is empty or missing.")
        return out

    keys = ["station_id", "measurement_date", "measurement_time"]

    sec = sections_df.copy()

    for col in keys:
        if col not in sec.columns:
            print(f"WARNING: Sections missing key column: {col}")
            return out

        sec[col] = sec[col].astype("string").str.strip()

    if "index" in sec.columns:
        sec["index"] = pd.to_numeric(sec["index"], errors="coerce")

    for col in ["w [m]", "h [m]", "q [l/s]", "factor [%]"]:
        if col not in sec.columns:
            print(f"WARNING: Sections missing required column: {col}")
            return out

    sec["w [m]"] = pd.to_numeric(sec["w [m]"], errors="coerce")
    sec["h [m]"] = pd.to_numeric(sec["h [m]"], errors="coerce")
    sec["q [l/s]"] = pd.to_numeric(sec["q [l/s]"], errors="coerce")
    sec["factor [%]"] = pd.to_numeric(sec["factor [%]"], errors="coerce")

    nivus = out[out["instrument"] == "nivus"].copy()

    if nivus.empty:
        return out

    for col in keys:
        nivus[col] = nivus[col].astype("string").str.strip()

    for key_vals, pts in nivus.groupby(keys, dropna=False):
        pts = pts.sort_values("point_index")
        pts_indices = pts.index.tolist()

        sec_group = sec.copy()

        for k, v in zip(keys, key_vals):
            sec_group = sec_group[sec_group[k].astype("string").str.strip() == str(v)]

        if "index" in sec_group.columns:
            sec_group = sec_group.sort_values("index")

        if len(sec_group) != len(pts) + 2:
            print(
                f"WARNING: Nivus mismatch for {key_vals}: "
                f"points={len(pts)}, sections={len(sec_group)}"
            )
            continue

        for i, row_idx in enumerate(pts_indices):
            if i == 0:
                s = sec_group.iloc[[0, 1]]
            elif i == len(pts_indices) - 1:
                s = sec_group.iloc[[-2, -1]]
            else:
                s = sec_group.iloc[[i + 1]]

            area_m2 = (s["w [m]"] * s["h [m]"]).sum()
            q_ls = s["q [l/s]"].sum()
            percent_q = s["factor [%]"].sum()

            out.loc[row_idx, "area_m2"] = area_m2
            out.loc[row_idx, "q_ls"] = q_ls
            out.loc[row_idx, "q_m3s"] = q_ls / 1000.0
            out.loc[row_idx, "percent_q"] = percent_q

    return out


def normalize_points_dataframe(
    points_df: pd.DataFrame,
    sections_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    out = pd.DataFrame(index=points_df.index)

    # -------------------------
    # Metadata
    # -------------------------
    out["instrument"] = _coalesce(points_df, ["instrument", "source"])
    out["station_id"] = _coalesce(points_df, ["station_id"])
    out["measurement_date"] = _coalesce(points_df, ["measurement_date"])
    out["measurement_time"] = _coalesce(points_df, ["measurement_time"])

    out["measurement_date"] = _format_date_yyyymmdd(out["measurement_date"])
    out["measurement_time"] = _format_time_hhmmss(out["measurement_time"])

    # -------------------------
    # Point identity
    # -------------------------
    out["point_index"] = _to_numeric(
        _coalesce(points_df, ["point_index", "station", "index"])
    )

    out["point_label"] = _coalesce(
        points_df,
        [
            "vert_label",
            "station",
            "index",
        ],
    )

    # -------------------------
    # Geometry
    # -------------------------
    out["distance_m"] = _to_numeric(
        _coalesce(points_df, ["location_m", "progr_m", "pos [m]"])
    )

    out["depth_m"] = _to_numeric(
        _coalesce(points_df, ["depth_m", "prof_m", "h [m]"])
    )

    # -------------------------
    # Velocity
    # -------------------------
    out["velocity_mean_m_s"] = _to_numeric(
        _coalesce(points_df, ["velocity_m_s", "vel_media_vert_ms", "v [m/s]"])
    )

    # -------------------------
    # Area and discharge
    # -------------------------
    out["area_m2"] = _to_numeric(
        _coalesce(points_df, ["area_m2"])
    )

    out["q_m3s"] = _to_numeric(
        _coalesce(points_df, ["discharge_m3_s", "q_m3s"])
    )

    out["q_ls"] = out["q_m3s"] * 1000.0

    out["percent_q"] = _to_numeric(
        _coalesce(points_df, ["percent_discharge", "q_percent"])
    )

    # -------------------------
    # Temperature
    # -------------------------
    out["temperature_c"] = _to_numeric(
        _coalesce(points_df, ["temperature_c", "t [°C]"])
    )

    # -------------------------
    # Provenance
    # -------------------------
    out["source_csv"] = _coalesce(points_df, ["source_csv"])
    out["source_run_dir"] = _coalesce(points_df, ["source_run_dir"])

    # -------------------------
    # Nivus enrichment from Sections
    # -------------------------
    nivus_mask = out["instrument"].astype("string").str.lower() == "nivus"

    if nivus_mask.any() and sections_df is not None:
        print("Applying Nivus section enrichment...")
        out = _enrich_nivus_from_sections(out, sections_df)

    return out[CANONICAL_COLUMNS]


def run(config_path: Path) -> Path:
    cfg = load_config(config_path)
    run_dir = create_run("normalize_points", config_path)

    normalize_cfg = cfg.get("normalize_points", {})

    points_file = Path(
        normalize_cfg.get(
            "points_file",
            "database/data_groups/Points/points_all.csv",
        )
    )

    sections_file = Path(
        normalize_cfg.get(
            "sections_file",
            "database/data_groups/Sections/sections_all.csv",
        )
    )

    output_file = Path(
        normalize_cfg.get(
            "output_file",
            "database/normalized/Points/points_normalized.csv",
        )
    )

    output_file.parent.mkdir(parents=True, exist_ok=True)

    points_df = pd.read_csv(points_file)
    sections_df = pd.read_csv(sections_file) if sections_file.exists() else None

    out = normalize_points_dataframe(points_df, sections_df)

    out.to_csv(output_file, index=False)

    print(f"Input rows: {len(points_df)}")
    print(f"Output rows: {len(out)}")
    print(f"Saved: {output_file}")
    print(f"Run created: {run_dir}")

    return run_dir