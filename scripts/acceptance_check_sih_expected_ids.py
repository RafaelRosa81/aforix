from __future__ import annotations

from pathlib import Path

import pandas as pd


OUTPUT_DIR = Path("outputs_acceptance/sih")

EXPECTED = {
    "ACCF001": {
        "station_id": "7071",
        "instrument": "flowtracker",
        "id_tipo_actuacion": "4",
        "id_instrumento": "501",
        "id_tipo_aforo": "57",
        "id_instrumentos_rangos": "11",
    },
    "ACCM001": {
        "station_id": "7071",
        "instrument": "molinete",
        "id_tipo_actuacion": "4",
        "id_instrumento": "19",
        "id_tipo_aforo": "57",
        "id_instrumentos_rangos": "11",
    },
}


def _read_one(path: Path) -> pd.Series:
    df = pd.read_csv(path, dtype=str).fillna("")
    assert len(df) == 1, f"{path.name}: expected exactly 1 row, got {len(df)}"
    return df.iloc[0]


def main() -> None:
    checks: list[dict[str, str]] = []

    metadata_path = OUTPUT_DIR / "sih_export_metadata.csv"
    if metadata_path.exists():
        metadata = pd.read_csv(metadata_path, dtype=str).fillna("")
    else:
        metadata = pd.DataFrame()

    for export_id, expected in EXPECTED.items():
        matches = metadata[metadata.get("export_id", pd.Series(dtype=str)) == export_id] if not metadata.empty else pd.DataFrame()
        metadata_ok = (
            len(matches) == 1
            and str(matches.iloc[0].get("status", "")).strip().lower() == "success"
        )
        checks.append({
            "check": f"{export_id}:metadata_success",
            "status": "PASS" if metadata_ok else "FAIL",
            "detail": (
                matches.iloc[0].to_dict() if len(matches) == 1 else f"matches={len(matches)}"
            ),
        })

        if export_id == "ACCF001":
            suffix = "7071_20260120_141519"
        else:
            suffix = "7071_20260120_142300"

        actuacion_path = OUTPUT_DIR / f"ID_{export_id}_actuacion_{suffix}.csv"
        aforo_path = OUTPUT_DIR / f"ID_{export_id}_aforo_{suffix}.csv"

        if not actuacion_path.exists() or not aforo_path.exists():
            checks.append({
                "check": f"{export_id}:expected_ids",
                "status": "FAIL",
                "detail": "expected actuacion/aforo CSV missing",
            })
            continue

        actuacion = _read_one(actuacion_path)
        aforo = _read_one(aforo_path)

        observed = {
            "id_tipo_actuacion": str(actuacion.get("id_tipo_actuacion", "")).strip(),
            "id_instrumento": str(aforo.get("id_instrumento", "")).strip(),
            "id_tipo_aforo": str(aforo.get("id_tipo_aforo", "")).strip(),
            "id_instrumentos_rangos": str(aforo.get("id_instrumentos_rangos", "")).strip(),
        }
        wanted = {
            "id_tipo_actuacion": expected["id_tipo_actuacion"],
            "id_instrumento": expected["id_instrumento"],
            "id_tipo_aforo": expected["id_tipo_aforo"],
            "id_instrumentos_rangos": expected["id_instrumentos_rangos"],
        }

        checks.append({
            "check": f"{export_id}:expected_ids",
            "status": "PASS" if observed == wanted else "FAIL",
            "detail": f"observed={observed}; expected={wanted}",
        })

    report = pd.DataFrame(checks)
    report_dir = Path("runs_acceptance/_checks")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "sih_expected_ids_acceptance.csv"
    report.to_csv(report_path, index=False, encoding="utf-8-sig")

    n_pass = int(report["status"].eq("PASS").sum())
    n_fail = int(report["status"].eq("FAIL").sum())

    print("Aforix SIH expected-ID acceptance")
    print("================================")
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
