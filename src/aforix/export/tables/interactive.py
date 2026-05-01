from __future__ import annotations

from pathlib import Path

from .config import get_normalized_root, enabled_instruments
from .runner import (
    ExportRequest,
    available_points,
    discover_instruments,
    discover_normalized_tables,
    load_normalized_table,
    normalize_point_token,
    parameter_columns,
    run_export_tables,
)


def _choose_one(title: str, options: list[str], default_idx: int = 0) -> str:
    if not options:
        raise ValueError(f"No options available for: {title}")
    print(f"\n{title}:")
    for i, opt in enumerate(options):
        suffix = " [default]" if i == default_idx else ""
        print(f"[{i}] {opt}{suffix}")
    raw = input(f"Select {title.lower()} [{default_idx}]: ").strip()
    if raw == "":
        return options[default_idx]
    if raw.isdigit():
        idx = int(raw)
        if 0 <= idx < len(options):
            return options[idx]
    matches = [o for o in options if o.lower() == raw.lower()]
    if matches:
        return matches[0]
    raise ValueError(f"Invalid selection '{raw}'. Choose an index between 0 and {len(options)-1}, or one of: {', '.join(options)}")


def _choose_many(title: str, options: list[str], empty_label: str = "all", allow_codes: bool = False) -> list[str]:
    print(f"\n{title}:")
    for i, opt in enumerate(options):
        print(f"[{i}] {opt}")
    raw = input(f"Select indices/codes separated by spaces, or empty = {empty_label}: ").strip()
    if raw == "":
        return []
    selected: list[str] = []
    invalid: list[str] = []
    option_lower = {o.lower(): o for o in options}
    option_points = {normalize_point_token(o).lower(): o for o in options}
    for token in raw.split():
        token_clean = token.strip()
        if token_clean.lower().startswith("idx:") and token_clean[4:].isdigit():
            idx = int(token_clean[4:])
            if 0 <= idx < len(options):
                selected.append(options[idx])
                continue
        if token_clean.startswith("[") and token_clean.endswith("]") and token_clean[1:-1].isdigit():
            idx = int(token_clean[1:-1])
            if 0 <= idx < len(options):
                selected.append(options[idx])
                continue
        if token_clean.isdigit() and 0 <= int(token_clean) < len(options):
            selected.append(options[int(token_clean)])
            continue
        if allow_codes:
            normalized = normalize_point_token(token_clean).lower()
            if normalized in option_points:
                selected.append(option_points[normalized])
                continue
        if token_clean.lower() in option_lower:
            selected.append(option_lower[token_clean.lower()])
            continue
        invalid.append(token_clean)
    if invalid:
        raise ValueError(
            "Invalid selection(s): " + ", ".join(invalid) +
            ". Use list indices, station codes such as P21 / 21, or idx:3 / [3]."
        )
    return list(dict.fromkeys(selected))


def _filter_by_instrument(df, instrument: str):
    if instrument.lower() == "all" or "instrument" not in df.columns:
        return df
    return df[df["instrument"].astype(str).str.lower() == instrument.lower()]


def _filter_by_points(df, points: list[str]):
    if not points:
        return df
    point_col = "station_id" if "station_id" in df.columns else None
    if point_col is None:
        return df
    wanted = {normalize_point_token(p) for p in points}
    return df[df[point_col].map(normalize_point_token).isin(wanted)]


def _has_csv_files(path: Path) -> bool:
    return path.is_dir() and any(path.glob("*.csv"))


def _looks_like_instrument_layout(root: Path, config: dict) -> bool:
    enabled = enabled_instruments(config)
    dirs = [p for p in root.iterdir() if p.is_dir()] if root.exists() else []
    if not dirs:
        return False
    if enabled and any(p.name.lower() in enabled for p in dirs):
        return True
    return any(_has_csv_files(child) for parent in dirs for child in parent.iterdir() if child.is_dir())


def _instrument_dirs(root: Path, config: dict) -> list[str]:
    enabled = enabled_instruments(config)
    values = []
    for p in root.iterdir() if root.exists() else []:
        if not p.is_dir():
            continue
        if enabled is not None and p.name.lower() not in enabled:
            continue
        if any(child.is_dir() and _has_csv_files(child) for child in p.iterdir()):
            values.append(p.name)
    return sorted(values, key=str.lower)


def _tables_for_instrument(root: Path, instrument: str) -> list[str]:
    base = root / instrument
    if not base.exists():
        return []
    return sorted([p.name for p in base.iterdir() if _has_csv_files(p)], key=str.lower)


def _table_dirs_for_instrument_selection(root: Path, instrument: str, table: str) -> tuple[list[Path], str]:
    if instrument.lower() == "all":
        dirs = [root / inst / table for inst in _instrument_dirs(root, {}) if _has_csv_files(root / inst / table)]
        return dirs, "all"
    tdir = root / instrument / table
    return ([tdir] if _has_csv_files(tdir) else []), instrument


def _load_table_dirs(dirs: list[Path], selected_instrument: str):
    import pandas as pd

    frames = []
    source_files = []
    for d in dirs:
        inst = d.parent.name
        for f in sorted(d.glob("*.csv")):
            df = pd.read_csv(f)
            if "instrument" not in df.columns:
                df.insert(0, "instrument", inst)
            frames.append(df)
            source_files.append(f)
    if not frames:
        raise FileNotFoundError("No CSV files found for selected instrument/table.")
    out = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
    return out, source_files


def run_interactive_export_tables(config: dict):
    root = get_normalized_root(config)
    print(f"Source: database/normalized (stable normalized data)")
    print(f"\n📂 Detecting normalized data in: {root}")

    if not root.exists():
        raise FileNotFoundError(f"Normalized root not found: {root}")

    if _looks_like_instrument_layout(root, config):
        instruments = _instrument_dirs(root, config)
        if not instruments:
            raise FileNotFoundError(f"No instrument folders with normalized tables found in {root}")
        instrument = _choose_one("Available instruments", ["all"] + instruments, default_idx=0)

        if instrument.lower() == "all":
            table_sets = [set(_tables_for_instrument(root, inst)) for inst in instruments]
            tables = sorted(set.union(*table_sets), key=str.lower) if table_sets else []
        else:
            tables = _tables_for_instrument(root, instrument)
        if not tables:
            raise FileNotFoundError(f"No normalized tables found for instrument selection: {instrument}")
        default_table_idx = next((i for i, t in enumerate(tables) if t.lower() == "summary"), 0)
        table = _choose_one("Available normalized tables", tables, default_idx=default_table_idx)
        dirs, instrument_tag = _table_dirs_for_instrument_selection(root, instrument, table)
        df, _ = _load_table_dirs(dirs, instrument_tag)
    else:
        tables = discover_normalized_tables(config)
        if not tables:
            raise FileNotFoundError(f"No normalized tables found in {root}")
        default_table_idx = next((i for i, t in enumerate(tables) if t.lower() == "summary"), 0)
        table = _choose_one("Available normalized tables", tables, default_idx=default_table_idx)
        df, _ = load_normalized_table(config, table)
        instruments = discover_instruments(df, config)
        instrument_options = ["all"] + instruments if instruments else ["all"]
        instrument = _choose_one("Available instruments", instrument_options, default_idx=0)
        df = _filter_by_instrument(df, instrument)

    points = available_points(df)
    selected_points = _choose_many("Available points/stations", points, empty_label="all", allow_codes=True) if points else []
    df_ip = _filter_by_points(df, selected_points)

    params = parameter_columns(df_ip, include_metadata=False)
    selected_params = _choose_many("Available parameters", params, empty_label="all") if params else []

    early = input("\nEarly date YYYYMMDD, or empty: ").strip() or None
    late = input("Late date YYYYMMDD, or empty: ").strip() or None
    grouping = input("Grouping (none/monthly/daily) [monthly]: ").strip().lower() or "monthly"
    if grouping not in {"none", "monthly", "daily"}:
        raise ValueError("Grouping must be one of: none, monthly, daily")
    pivot = grouping in {"monthly", "daily"}
    aggregation = input("Aggregation for grouped export (mean/sum/median/min/max/first) [mean]: ").strip().lower() or "mean"
    fmt = input("Output format (xlsx/csv) [xlsx]: ").strip().lower() or "xlsx"

    req = ExportRequest(
        table=table,
        instrument=instrument,
        points=tuple(selected_points),
        parameters=tuple(selected_params),
        early_date=early,
        late_date=late,
        grouping=grouping,
        fmt=fmt,
        pivot=pivot,
        aggregation=aggregation,
    )
    result = run_export_tables(config, req)
    print(f"\n✅ Export completed:\n{result.output_file}")
    print(f"🧾 Metadata:\n{result.metadata_file}")
    print(f"Rows exported: {result.row_count}")
    return result
