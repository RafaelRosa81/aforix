from __future__ import annotations

import argparse


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aforix — export measurements to SIH format")

    parser.add_argument("-c", "--config", required=True, help="Path to main YAML config")
    parser.add_argument("--sih-config", required=True, help="Path to SIH YAML config")
    parser.add_argument("--selection-file", help="CSV selection file for massive exports")
    parser.add_argument("--interactive", action="store_true", help="Run interactive export mode")

    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    print("\nAforix — SIH export")
    print("====================")
    print(f"Main config: {args.config}")
    print(f"SIH config: {args.sih_config}")

    if args.selection_file:
        print(f"Selection file: {args.selection_file}")

    if args.interactive:
        print("Interactive mode requested")

    print("\n⚠️ SIH export logic not implemented yet.")
    print("This branch currently consolidates architecture and configuration only.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
