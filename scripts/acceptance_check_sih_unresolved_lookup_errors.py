from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml


CONFIG = Path("configs/sih/sih_acceptance.yaml")
SELECTION = Path("configs/sih/selection_acceptance.csv")


def main() -> None:
    root = Path.cwd().resolve()
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    output_dir = root / cfg["sih"]["output"]["output_dir"]
    selection = pd.read_csv(SELECTION, dtype=str).fillna("")

    checks: list[dict[str, object]] = []

    metadata_path = output_dir / "sih_export_metadata.csv"
    metadata_exists = metadata_path.exists()
    checks.append({
        "check": "metadata_exists",
        "status": "PASS" if metadata_exists else "FAIL",
        "detail": str(metadata_path),
    })

    if metadata_exists:
        metadata = pd.read_csv(metadata_path, dtype=str).fillna("")
        expected_keys = set(
            zip(
                selection["export_id"],
                selection["instrument"],
                selection["station_id"],
                selection["measurement_date"],
                selection["measurement_time"],
            )
        )
        observed_keys = set(
            zip(
                metadata.get("export_id", pd.Series(dtype=str)),
                metadata.get("instrument", pd.Series(dtype=str)),
                metadata.get("station_id", pd.Series(dtype=str)),
                metadata.get("measurement_date", pd.Series(dtype=str)),
                metadata.get("measurement_time", pd.Series(dtype=str)),
            )
        )

        rows_ok = len(metadata) == len(selection) and observed_keys == expected_keys
        checks.append({
            "check": "metadata_identity",
            "status": "PASS" if rows_ok else "FAIL",
            "detail": f"rows={len(metadata)} expected={len(selection)}",
        })

        all_errors = (
            "status" in metadata.columns
            and metadata["status"].eq("error").all()
        )
        checks.append({
            "check": "all_selected_measurements_fail_explicitly",
            "status": "PASS" if all_errors else "FAIL",
            "detail": (
                f"statuses={metadata.get('status', pd.Series(dtype=str)).tolist()}"
            ),
        })

        errors = metadata.get("error", pd.Series([""] * len(metadata), dtype=str)).astype(str)
        semantic_error_ok = errors.str.contains(
            "instrumentos_rangos", case=False, regex=False
        ).all() and errors.str.contains(
            "Velocimetro puntual", case=False, regex=False
        ).all()
        checks.append({
            "check": "error_identifies_unresolved_configured_lookup",
            "status": "PASS" if semantic_error_ok else "FAIL",
            "detail": " | ".join(errors.tolist()),
        })
    else:
        metadata = pd.DataFrame()
        for name in [
            "metadata_identity",
            "all_selected_measurements_fail_explicitly",
            "error_identifies_unresolved_configured_lookup",
        ]:
            checks.append({
                "check": name,
                "status": "FAIL",
                "detail": "metadata unavailable",
            })

    measurement_csvs = sorted(
        p for p in output_dir.glob("ID_*.csv")
        if p.name != "sih_export_metadata.csv"
    ) if output_dir.exists() else []
    no_partial_outputs = len(measurement_csvs) == 0
    checks.append({
        "check": "no_partial_measurement_csvs",
        "status": "PASS" if no_partial_outputs else "FAIL",
        "detail": f"unexpected_files={[p.name for p in measurement_csvs]}",
    })

    report = pd.DataFrame(checks)
    report_dir = root / "runs_acceptance" / "_checks"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "sih_unresolved_lookup_errors_acceptance.csv"
    report.to_csv(report_path, index=False, encoding="utf-8-sig")

    n_pass = int(report["status"].eq("PASS").sum())
    n_fail = int(report["status"].eq("FAIL").sum())

    print("Aforix SIH unresolved-lookup error acceptance")
    print("============================================")
    print(f"Output directory: {output_dir}")
    print(f"Checks: {len(report)}")
    print(f"PASS: {n_pass}")
    print(f"FAIL: {n_fail}")
    print(f"Report: {report_path}")

    if n_fail:
        print("")
        print("Failed checks:")
        print(report.loc[report["status"] == "FAIL"].to_string(index=False))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
