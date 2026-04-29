from pathlib import Path
import pandas as pd

from aforix.config.loader import load_config
from aforix.runs.manager import create_run


CANONICAL_COLUMNS = [
    "instrument",
    "station_id",
    "station_name",
    "measurement_date",
    "measurement_time",
    "q_total_m3s",
    "q_total_ls",
    "area_total_m2",
    "width_total_m",
    "velocity_mean_m_s",
    "depth_mean_m",
    "temperature_c",
    "source_csv",
    "source_run_dir",
]


def _to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _first_existing(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    for col in columns:
        if col in df.columns:
            return df[col]
    return pd.Series([pd.NA] * len(df), index=df.index)


def _coalesce(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    """Return first non-null value across several possible columns (robust version)."""
    valid_cols = [col for col in columns if col in df.columns]

    if not valid_cols:
        return pd.Series([pd.NA] * len(df), index=df.index)

    out = df[valid_cols[0]].copy()

    for col in valid_cols[1:]:
        out = out.combine_first(df[col])

    return out


def _format_date_yyyymmdd(series: pd.Series) -> pd.Series:
    s = series.astype("string").str.strip()
    s = s.str.replace("-", "", regex=False)
    s = s.str.replace("/", "", regex=False)
    return s


def _format_time_hhmmss(series: pd.Series) -> pd.Series:
    s = series.astype("string").str.strip()
    s = s.str.replace(":", "", regex=False)
    s = s.str.replace(r"\.0$", "", regex=True)
    return s.str.zfill(6)


def normalize_summary_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)

    # -------------------------
    # Metadata
    # -------------------------
    out["instrument"] = _coalesce(df, ["instrument", "source"])
    out["station_id"] = _coalesce(df, ["station_id"])

    out["station_name"] = _coalesce(
        df,
        [
            "station_name",  # preferred if added during ingest
            "site_name",     # FlowTracker
            "nombre",        # Molinete
            "name",          # Nivus
        ],
    )

    out["measurement_date"] = _coalesce(df, ["measurement_date"])
    out["measurement_time"] = _coalesce(df, ["measurement_time"])

    out["measurement_date"] = _format_date_yyyymmdd(out["measurement_date"])
    out["measurement_time"] = _format_time_hhmmss(out["measurement_time"])

    # -------------------------
    # Discharge
    # -------------------------
    ft_q_m3s = _to_numeric(_coalesce(df, ["total_discharge_m3_s"]))
    ml_q_m3s = _to_numeric(_coalesce(df, ["q_m3s"]))
    nv_q_ls = _to_numeric(_coalesce(df, ["q [l/s]"]))

    out["q_total_m3s"] = (
        ft_q_m3s
        .combine_first(ml_q_m3s)
        .combine_first(nv_q_ls / 1000.0)
    )

    out["q_total_ls"] = (
        (ft_q_m3s * 1000.0)
        .combine_first(ml_q_m3s * 1000.0)
        .combine_first(nv_q_ls)
    )

    # -------------------------
    # Area
    # -------------------------
    out["area_total_m2"] = (
        _to_numeric(_coalesce(df, ["total_area_m2"]))
        .combine_first(_to_numeric(_coalesce(df, ["area_m2"])))
        .combine_first(_to_numeric(_coalesce(df, ["a [m²]"])))
    )

    # -------------------------
    # Width
    # -------------------------
    out["width_total_m"] = (
        _to_numeric(_coalesce(df, ["total_width_m"]))
        .combine_first(_to_numeric(_coalesce(df, ["ancho_m"])))
        .combine_first(_to_numeric(_coalesce(df, ["w [m]"])))
    )

    # -------------------------
    # Mean velocity
    # -------------------------
    out["velocity_mean_m_s"] = (
        _to_numeric(_coalesce(df, ["mean_velocity_m_s"]))
        .combine_first(_to_numeric(_coalesce(df, ["vel_media_ms"])))
        .combine_first(_to_numeric(_coalesce(df, ["v_mean [m/s]"])))
    )

    # -------------------------
    # Mean depth
    # -------------------------
    out["depth_mean_m"] = (
        _to_numeric(_coalesce(df, ["mean_depth_m"]))
        .combine_first(_to_numeric(_coalesce(df, ["prof_media_m"])))
        .combine_first(_to_numeric(_coalesce(df, ["h_mean [m]"])))
    )

    # -------------------------
    # Temperature
    # -------------------------
    out["temperature_c"] = (
        _to_numeric(_coalesce(df, ["mean_temp_degc"]))
        .combine_first(_to_numeric(_coalesce(df, ["t [°C]"])))
    )

    # -------------------------
    # Provenance
    # -------------------------
    out["source_csv"] = _coalesce(df, ["source_csv"])
    out["source_run_dir"] = _coalesce(df, ["source_run_dir"])

    return out[CANONICAL_COLUMNS]


def run(config_path: Path) -> Path:
    cfg = load_config(config_path)
    run_dir = create_run("normalize_summary", config_path)

    normalize_cfg = cfg.get("normalize_summary", {})

    input_file = Path(
        normalize_cfg.get(
            "input_file",
            "database/data_groups/Summary/summary_all.csv",
        )
    )

    output_file = Path(
        normalize_cfg.get(
            "output_file",
            "database/normalized/Summary/summary_normalized.csv",
        )
    )

    output_file.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_file)
    out = normalize_summary_dataframe(df)

    out.to_csv(output_file, index=False)

    print(f"Input rows: {len(df)}")
    print(f"Output rows: {len(out)}")
    print(f"Saved: {output_file}")
    print(f"Run created: {run_dir}")

    return run_dir