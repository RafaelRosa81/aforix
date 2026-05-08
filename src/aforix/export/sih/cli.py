from __future__ import annotations

import argparse
from pathlib import Path

from aforix.export.sih.config import (
    get_default_selection_file,
    load_sih_config,
)
from aforix.export.sih.interactive import build_interactive_selection
from aforix.export.sih.runner import (
    SihExportRequest,
    run_sih_export,
)



def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aforix — export measurements to SIH format")

    parser.add_argument("-c", "--config", required=True, help="Path to main YAML config")
    parser.add_argument("--sih-config", required=True, help="Path to SIH YAML config")
    parser.add_argument("--selection-file", help="CSV selection file for massive exports")
    parser.add_argument("--interactive", action="store_true", help="Run interactive export mode")

    return parser.parse_args(argv)



def main(argv=None) -> int:
    args = parse_args(argv)

    sih_config = load_sih_config(args.sih_config)

    if args.interactive:
        selection_file = build_interactive_selection(sih_config)
    else:
        selection_file = (
            Path(args.selection_file)
            if args.selection_file
            else get_default_selection_file(sih_config)
        )

    request = SihExportRequest(
        sih_config_path=Path(args.sih_config),
        selection_file=selection_file,
        interactive=args.interactive,
    )

    result = run_sih_export(request)

    print("\nAforix — SIH export")
    print("====================")
    print(f"Output directory: {result.output_dir}")
    print(f"Generated files: {len(result.exported_files)}")

    for path in result.exported_files:
        print(f" - {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
