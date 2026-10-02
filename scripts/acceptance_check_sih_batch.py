from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from aforix.export.sih.schema import SDH_ACTUACIONES_COLUMNS, SDH_AFOROS_COLUMNS


CONFIG = Path("configs/sih/sih_acceptance.yaml")
SELECTION = Path("configs/sih/selection_acceptance.csv")


def main() -> None:
    root = Path.cwd().resolve()
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    sih = cfg["sih"]

    output_dir = root / sih["output"]["output_dir"]
    normalized = root / sih["inputs"]["normalized_input_dir"] / "Summary.csv"
    selection = pd.read_csv(SELECTION, dtype=str)
    summary = pd.read_csv(
        normalized,
        dtype={
            "station_id": "string",
            "measurement_date": "string",
            "measurement_time": "string",
        },
    )

    checks: list[dict[str, object]] = []

    isolation_ok = (
        "outputs_acceptance" in output_dir.parts
        and "database_acceptance" in Path(sih["inputs"]["normalized_input_dir"]).parts
        and "database_acceptance" in Path(sih["inputs"]["raw_canonical_input_dir"]).parts
    )
    checks.append({
        "check": "acceptance_isolation",
        "status": "PASS" if isolation_ok else "FAIL",
        "detail": f"output={output_dir}",
    })

    metadata_path = output_dir / "sih_export_metadata.csv"
    metadata_ok = metadata_path.exists()
    checks.append({
        "check": "metadata_exists",
        "status": "PASS" if metadata_ok else "FAIL",
        "detail": str(metadata_path),
    })

    if metadata_ok:
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
        success_ok = (
            len(metadata) == len(selection)
            and metadata.get("status", pd.Series(dtype=str)).eq("success").all()
            and observed_keys == expected_keys
        )
        checks.append({
            "check": "metadata_success_and_identity",
            "status": "PASS" if success_ok else "FAIL",
            "detail": (
                f"rows={len(metadata)}; "
                f"statuses={metadata.get('status', pd.Series(dtype=str)).tolist()}"
            ),
        })
    else:
        metadata = pd.DataFrame()
        checks.append({
            "check": "metadata_success_and_identity",
            "status": "FAIL",
            "detail": "metadata unavailable",
        })

    expected_files: list[Path] = []
    for row in selection.itertuples(index=False):
        stem = f"ID_{row.export_id}"
        suffix = f"{row.station_id}_{row.measurement_date}_{row.measurement_time}.csv"
        expected_files.extend([
            output_dir / f"{stem}_actuacion_{suffix}",
            output_dir / f"{stem}_aforo_{suffix}",
        ])

    files_ok = all(p.exists() for p in expected_files)
    checks.append({
        "check": "expected_measurement_files",
        "status": "PASS" if files_ok else "FAIL",
        "detail": f"expected={len(expected_files)} missing={[str(p) for p in expected_files if not p.exists()]}",
    })

    schema_ok = files_ok
    if files_ok:
        for p in expected_files:
            df = pd.read_csv(p, dtype=str).fillna("")
            expected_cols = SDH_ACTUACIONES_COLUMNS if "_actuacion_" in p.name else SDH_AFOROS_COLUMNS
            if list(df.columns) != expected_cols or len(df) != 1:
                schema_ok = False
                break
    checks.append({
        "check": "sih_schema",
        "status": "PASS" if schema_ok else "FAIL",
        "detail": "one row per output with exact configured SIH schema",
    })

    fidelity_ok = files_ok
    details: list[str] = []
    if files_ok:
        for row in selection.itertuples(index=False):
            src = summary[
                (summary["instrument"].astype(str) == row.instrument)
                & (summary["station_id"].astype(str) == row.station_id)
                & (summary["measurement_date"].astype(str) == row.measurement_date)
                & (summary["measurement_time"].astype(str) == row.measurement_time)
            ]
            if len(src) != 1:
                fidelity_ok = False
                details.append(f"{row.export_id}: normalized matches={len(src)}")
                continue

            aforo_path = output_dir / (
                f"ID_{row.export_id}_aforo_{row.station_id}_"
                f"{row.measurement_date}_{row.measurement_time}.csv"
            )
            actuacion_path = output_dir / (
                f"ID_{row.export_id}_actuacion_{row.station_id}_"
                f"{row.measurement_date}_{row.measurement_time}.csv"
            )
            aforo = pd.read_csv(aforo_path, dtype=str).fillna("").iloc[0]
            actuacion = pd.read_csv(actuacion_path, dtype=str).fillna("").iloc[0]
            source = src.iloc[0]

            if aforo["id_estacion"] != row.station_id or actuacion["id_estacion"] != row.station_id:
                fidelity_ok = False
                details.append(f"{row.export_id}: station identity mismatch")

            expected_dt = (
                f"{row.measurement_date[6:8]}/{row.measurement_date[4:6]}/"
                f"{row.measurement_date[:4]} "
                f"{row.measurement_time[:2]}:{row.measurement_time[2:4]}:{row.measurement_time[4:6]}"
            )
            if (
                aforo["fecha_inicio"] != expected_dt
                or aforo["fecha_fin"] != expected_dt
                or actuacion["fecha"] != expected_dt
            ):
                fidelity_ok = False
                details.append(f"{row.export_id}: datetime mismatch")

            for out_col, source_col in [
                ("caudal", "q_total_m3s"),
                ("ancho", "width_total_m"),
                ("profundidad", "depth_mean_m"),
                ("seccion", "area_total_m2"),
                ("velocidad_media", "velocity_mean_m_s"),
            ]:
                out_v = pd.to_numeric(pd.Series([aforo[out_col]]), errors="coerce").iloc[0]
                src_v = pd.to_numeric(pd.Series([source[source_col]]), errors="coerce").iloc[0]
                same_missing = pd.isna(out_v) and pd.isna(src_v)
                same_value = pd.notna(out_v) and pd.notna(src_v) and abs(out_v - src_v) <= 1e-12
                if not (same_missing or same_value):
                    fidelity_ok = False
                    details.append(
                        f"{row.export_id}: {out_col}={aforo[out_col]!r} source={source[source_col]!r}"
                    )

    checks.append({
        "check": "normalized_identity_numeric_fidelity",
        "status": "PASS" if fidelity_ok else "FAIL",
        "detail": "; ".join(details),
    })

    report = pd.DataFrame(checks)
    report_dir = root / "runs_acceptance" / "_checks"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "sih_batch_acceptance.csv"
    report.to_csv(report_path, index=False, encoding="utf-8-sig")

    n_pass = int(report["status"].eq("PASS").sum())
    n_fail = int(report["status"].eq("FAIL").sum())

    print("Aforix SIH batch acceptance")
    print("==========================")
    print(f"Output directory: {output_dir}")
    print(f"Selection rows: {len(selection)}")
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
