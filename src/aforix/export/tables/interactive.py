from __future__ import annotations

from .config import get_normalized_root
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
        if allow_codes:
            normalized = normalize_point_token(token_clean).lower()
            if normalized in option_points:
                selected.append(option_points[normalized])
                continue
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
        if token_clean.isdigit() and not allow_codes and 0 <= int(token_clean) < len(options):
            selected.append(options[int(token_clean)])
            continue
        if token_clean.lower() in option_lower:
            selected.append(option_lower[token_clean.lower()])
            continue
        invalid.append(token_clean)
    if invalid:
        raise ValueError(
            "Invalid selection(s): " + ", ".join(invalid) +
            ". For points, use station codes such as P21 / 21. To force an index, use idx:3 or [3]."
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


def run_interactive_export_tables(config: dict):
    root = get_normalized_root(config)
    print(f"Source: database/normalized (stable normalized data)")
    print(f"\n📂 Detecting normalized tables in: {root}")

    tables = discover_normalized_tables(config)
    if not tables:
        raise FileNotFoundError(f"No normalized tables found in {root}")
    default_table_idx = tables.index("Summary") if "Summary" in tables else 0
    table = _choose_one("Available normalized tables", tables, default_idx=default_table_idx)

    df, _ = load_normalized_table(config, table)

    instruments = discover_instruments(df, config)
    instrument_options = ["all"] + instruments if instruments else ["all"]
    instrument = _choose_one("Available instruments", instrument_options, default_idx=0)
    df_i = _filter_by_instrument(df, instrument)

    points = available_points(df_i)
    selected_points = _choose_many("Available points/stations", points, empty_label="all", allow_codes=True) if points else []
    df_ip = _filter_by_points(df_i, selected_points)

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
