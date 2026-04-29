from __future__ import annotations

import argparse

from .config import load_config
from .runner import ExportRequest, run_export_tables
from .interactive import run_interactive_export_tables


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Aforix — export tables from stable normalized data")
    p.add_argument("-c", "--config", required=True, help="Path to main YAML config")
    p.add_argument("--interactive", action="store_true", help="Run menu-driven mode")
    p.add_argument("--table", help="Normalized table name, e.g. Summary or Points")
    p.add_argument("--instrument", default="all", help="Instrument name or 'all'")
    p.add_argument("--points", nargs="*", default=[], help="Point/station codes, e.g. P21 21 P8")
    p.add_argument("--parameters", "--columns", dest="parameters", nargs="*", default=[], help="Columns/parameters to export")
    p.add_argument("--early-date", dest="early_date")
    p.add_argument("--late-date", dest="late_date")
    p.add_argument("--grouping", choices=["none", "monthly", "daily"], default="monthly")
    p.add_argument("--format", dest="fmt", choices=["xlsx", "csv"], default="xlsx")
    p.add_argument("--flat", action="store_true", help="Do not pivot even if grouping is provided")
    p.add_argument("--aggregation", choices=["mean", "sum", "median", "min", "max", "first"], default="mean")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    config = load_config(args.config)

    print("\nAforix — export tables")
    print("======================")

    if args.interactive:
        run_interactive_export_tables(config)
        return 0

    if not args.table:
        raise SystemExit("--table is required in non-interactive mode")

    req = ExportRequest(
        table=args.table,
        instrument=args.instrument,
        points=tuple(args.points or []),
        parameters=tuple(args.parameters or []),
        early_date=args.early_date,
        late_date=args.late_date,
        grouping=args.grouping,
        fmt=args.fmt,
        pivot=False if args.flat else args.grouping in {"monthly", "daily"},
        aggregation=args.aggregation,
    )

    result = run_export_tables(config, req)

    print(f"\n✅ Export completed:\n{result.output_file}")
    print(f"🧾 Metadata:\n{result.metadata_file}")
    print(f"Rows exported: {result.row_count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())