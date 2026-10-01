from __future__ import annotations

import argparse
import csv
import hashlib
from collections import Counter, defaultdict
from pathlib import Path


DEFAULT_SUFFIXES = {
    "FT": {".dis"},
    "ML": {".xls", ".xlsx"},
    "NV": {".xml"},
    "M9": None,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_files(raw_root: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for instrument, suffixes in DEFAULT_SUFFIXES.items():
        root = raw_root / instrument
        if not root.exists():
            continue

        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            if path.name == ".gitkeep":
                continue
            if suffixes is not None and path.suffix.lower() not in suffixes:
                continue

            rows.append(
                {
                    "instrument": instrument,
                    "relative_path": str(path.relative_to(raw_root)),
                    "filename": path.name,
                    "suffix": path.suffix.lower(),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )

    return rows


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_summary(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["instrument"])].append(row)

    summary: list[dict[str, object]] = []
    for instrument in sorted(DEFAULT_SUFFIXES):
        items = grouped.get(instrument, [])
        hashes = [str(row["sha256"]) for row in items]
        counts = Counter(hashes)
        summary.append(
            {
                "instrument": instrument,
                "files": len(items),
                "size_bytes": sum(int(row["size_bytes"]) for row in items),
                "unique_hashes": len(set(hashes)),
                "duplicate_files": sum(count - 1 for count in counts.values() if count > 1),
            }
        )
    return summary


def build_duplicate_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    by_hash: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_hash[str(row["sha256"])].append(row)

    out: list[dict[str, object]] = []
    for digest, items in sorted(by_hash.items()):
        if len(items) < 2:
            continue
        for row in items:
            out.append(
                {
                    "sha256": digest,
                    "duplicate_count": len(items),
                    "instrument": row["instrument"],
                    "relative_path": row["relative_path"],
                    "filename": row["filename"],
                    "size_bytes": row["size_bytes"],
                }
            )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a read-only physical inventory of real Aforix RAW inputs."
    )
    parser.add_argument("--raw-root", default="data/raw")
    parser.add_argument("--output-dir", default="runs_acceptance/_inventory")
    args = parser.parse_args()

    raw_root = Path(args.raw_root).resolve()
    output_dir = Path(args.output_dir).resolve()

    if not raw_root.exists() or not raw_root.is_dir():
        raise SystemExit(f"RAW root does not exist or is not a directory: {raw_root}")

    rows = discover_files(raw_root)
    summary = build_summary(rows)
    duplicates = build_duplicate_rows(rows)

    write_csv(
        output_dir / "raw_inventory.csv",
        rows,
        ["instrument", "relative_path", "filename", "suffix", "size_bytes", "sha256"],
    )
    write_csv(
        output_dir / "raw_inventory_summary.csv",
        summary,
        ["instrument", "files", "size_bytes", "unique_hashes", "duplicate_files"],
    )
    write_csv(
        output_dir / "raw_duplicate_hashes.csv",
        duplicates,
        ["sha256", "duplicate_count", "instrument", "relative_path", "filename", "size_bytes"],
    )

    print("Aforix real-data acceptance inventory")
    print("=" * 44)
    for row in summary:
        print(
            f'{row["instrument"]}: files={row["files"]}, '
            f'unique_hashes={row["unique_hashes"]}, '
            f'duplicate_files={row["duplicate_files"]}, '
            f'size_bytes={row["size_bytes"]}'
        )
    print(f"TOTAL: files={len(rows)}")
    print(f"Inventory written to: {output_dir}")


if __name__ == "__main__":
    main()
