"""Validation of normalized M9 transects without inventing discrete verticals."""
from pathlib import Path
import numpy as np
import pandas as pd

KEYS = ["instrument", "station_id", "measurement_date", "measurement_time", "source_file"]
SUMMARY_NUMERIC = ["q_total_m3s", "area_total_m2", "width_total_m", "sample_count",
                   "wetted_perimeter_m", "hydraulic_radius_m"]
POINT_NUMERIC = ["sample_number", "distance_m", "width_m", "depth_m",
                 "velocity_mean_m_s", "q_cumulative_m3s", "q_increment_m3s"]


def validate_m9(summary: pd.DataFrame | None, points: pd.DataFrame | None) -> pd.DataFrame:
    """Return issues only; an empty report means all implemented checks passed.

    Missing IVE inputs are reported for review, not filled or silently discarded.
    Q_mid is deliberately not equated with the manufacturer's Summary discharge.
    """
    rows = []

    def issue(table, rule, message, source=""):
        rows.append(dict(table=table, instrument="m9", source_file=source,
                         rule=rule, status="inconsistent", message=message))

    tables = {}
    for name, frame, numeric in (("Summary", summary, SUMMARY_NUMERIC),
                                  ("Points", points, POINT_NUMERIC)):
        if frame is None or frame.empty:
            issue(name, "missing_table", "No M9 rows available")
            continue
        missing = set(KEYS + numeric) - set(frame.columns)
        if missing:
            issue(name, "missing_columns", ", ".join(sorted(missing)))
            continue
        df = frame.copy()
        blank_keys = df[KEYS].isna() | df[KEYS].astype(str).apply(lambda col: col.str.strip().eq(""))
        if blank_keys.any().any():
            issue(name, "identity", "Missing measurement identity")
        for col in numeric:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            if not np.isfinite(df[col].to_numpy(dtype=float)).all():
                issue(name, "finite", f"{col} contains missing, nonnumeric or non-finite values")
        duplicates = KEYS + (["sample_number"] if name == "Points" else [])
        if df.duplicated(duplicates, keep=False).any():
            issue(name, "duplicate", "Repeated measurement/sample identity")
        nonnegative = ["area_total_m2", "hydraulic_radius_m"] if name == "Summary" else ["depth_m", "distance_m"]
        positive = ["width_total_m", "sample_count", "wetted_perimeter_m"] if name == "Summary" else ["width_m", "sample_number"]
        for col in nonnegative:
            if df[col].lt(0).any():
                issue(name, "range", f"{col} must be non-negative")
        for col in positive:
            if df[col].le(0).any():
                issue(name, "range", f"{col} must be positive")
        integer = "sample_count" if name == "Summary" else "sample_number"
        if df[integer].dropna().mod(1).ne(0).any():
            issue(name, "integer", f"{integer} must be an integer")
        tables[name] = df

    if len(tables) == 2:
        s, p = tables["Summary"], tables["Points"]
        sg = {key: group for key, group in s.groupby(KEYS, dropna=False)}
        pg = {key: group for key, group in p.groupby(KEYS, dropna=False)}
        for key in sg.keys() | pg.keys():
            source = str(key[-1])
            if key not in sg or key not in pg:
                issue("Summary/Points", "missing_pair", "Unmatched transect", source)
                continue
            if len(sg[key]) != 1:
                continue
            row = sg[key].iloc[0]
            samples = pg[key].sort_values("sample_number")
            if len(samples) != row["sample_count"]:
                issue("Points", "sample_count", "Sample count differs from Summary", source)
            if not np.array_equal(samples["sample_number"].to_numpy(), np.arange(1, len(samples) + 1)):
                issue("Points", "sample_sequence", "Expected sample numbers 1..N without gaps", source)
            if not np.allclose(samples["width_m"], row["width_total_m"], rtol=1e-8, atol=1e-8):
                issue("Points", "width", "Point width differs from Summary", source)
            if samples["distance_m"].gt(row["width_total_m"] + 1e-8).any():
                issue("Points", "position", "Point outside the section", source)
            if samples["distance_m"].duplicated().any():
                issue("Points", "ive_positions", "Repeated positions prevent IVE", source)
            q = samples["q_cumulative_m3s"]
            if not np.isclose(q.iloc[-1], row["q_total_m3s"], rtol=1e-8, atol=1e-8):
                issue("Summary/Points", "discharge", "Final cumulative discharge differs from Summary", source)
            expected = q.diff()
            expected.iloc[0] = q.iloc[0]
            if not np.allclose(samples["q_increment_m3s"], expected, rtol=1e-8, atol=1e-8):
                issue("Points", "increments", "Discharge increments disagree with cumulative discharge", source)
            perimeter = row["wetted_perimeter_m"]
            if perimeter > 0 and not np.isclose(row["hydraulic_radius_m"], row["area_total_m2"] / perimeter,
                                               rtol=1e-8, atol=1e-8):
                issue("Summary", "radius", "Radius differs from area / wetted perimeter", source)
    return pd.DataFrame(rows, columns=["table", "instrument", "source_file", "rule", "status", "message"])


def split_instruments(input_dir: Path, temporary_dir: Path):
    """Provide generic checks with non-M9 rows and M9 with its own schema.

    Preserve the old execution path exactly when M9 is absent. Consolidated
    normalized tables remain the input contract of the validation command.
    """
    tables = {}
    has_m9 = False
    for name in ("Summary", "Points"):
        path = input_dir / f"{name}.csv"
        df = pd.read_csv(path, dtype=str) if path.exists() else None
        if df is not None and "instrument" in df:
            mask = df["instrument"].fillna("").str.strip().str.casefold().eq("m9")
        else:
            mask = pd.Series(False, index=df.index) if df is not None else None
        tables[name] = (df, mask)
        has_m9 |= mask is not None and bool(mask.any())
    if not has_m9:
        return input_dir, True, None
    has_other = False
    m9 = {}
    # Other configured tables are copied unchanged for legacy checks.
    import shutil
    for path in input_dir.glob("*.csv"):
        shutil.copy2(path, temporary_dir / path.name)
    for name, (df, mask) in tables.items():
        m9[name] = df.loc[mask].copy() if df is not None else None
        if df is not None:
            others = df.loc[~mask]
            has_other |= not others.empty
            others.to_csv(temporary_dir / f"{name}.csv", index=False)
    return temporary_dir, has_other, validate_m9(m9["Summary"], m9["Points"])
