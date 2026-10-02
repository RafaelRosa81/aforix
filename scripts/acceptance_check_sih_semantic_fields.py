from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml


CONFIG = Path("configs/sih/sih_acceptance.yaml")
SELECTION = Path("configs/sih/selection_acceptance.csv")


def _norm(value: object) -> str:
    return str(value if value is not None else "").strip().casefold()


def main() -> None:
    root = Path.cwd().resolve()
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    sih = cfg["sih"]
    output_dir = root / sih["output"]["output_dir"]
    selection = pd.read_csv(SELECTION, dtype=str).fillna("")

    tipo_path = root / sih["lookup_files"]["tipos_aforos"]
    rango_path = root / sih["lookup_files"]["instrumentos_rangos"]
    tipos = pd.read_csv(tipo_path, dtype=str).fillna("")
    rangos = pd.read_csv(rango_path, dtype=str).fillna("")

    checks: list[dict[str, object]] = []

    # Configuration-level lookup resolvability. If a key is configured, it should
    # resolve to an actual lookup record rather than silently becoming blank.
    for instrument in sorted(selection["instrument"].unique()):
        inst_cfg = sih["instruments"][instrument]

        tipo_key = str(inst_cfg.get("tipo_aforo_lookup", "") or "").strip()
        if tipo_key:
            matches = tipos[tipos["descripcion"].map(_norm) == _norm(tipo_key)]
            checks.append({
                "check": f"{instrument}:tipo_aforo_lookup",
                "status": "PASS" if len(matches) == 1 else "FAIL",
                "detail": (
                    f"configured={tipo_key!r}; matches={len(matches)}; "
                    f"available={tipos['descripcion'].astype(str).tolist()}"
                ),
            })

        rango_key = str(inst_cfg.get("instrumentos_rangos_lookup", "") or "").strip()
        if rango_key:
            matches = rangos[rangos["descripcion"].map(_norm) == _norm(rango_key)]
            checks.append({
                "check": f"{instrument}:instrumentos_rangos_lookup",
                "status": "PASS" if len(matches) == 1 else "FAIL",
                "detail": (
                    f"configured={rango_key!r}; matches={len(matches)}; "
                    f"available={rangos['descripcion'].astype(str).tolist()}"
                ),
            })

    # Output-level semantic fields.
    for row in selection.itertuples(index=False):
        aforo_path = output_dir / (
            f"ID_{row.export_id}_aforo_{row.station_id}_"
            f"{row.measurement_date}_{row.measurement_time}.csv"
        )
        actuacion_path = output_dir / (
            f"ID_{row.export_id}_actuacion_{row.station_id}_"
            f"{row.measurement_date}_{row.measurement_time}.csv"
        )

        if not aforo_path.exists() or not actuacion_path.exists():
            checks.append({
                "check": f"{row.export_id}:semantic_output_fields",
                "status": "FAIL",
                "detail": "expected SIH output file missing",
            })
            continue

        aforo = pd.read_csv(aforo_path, dtype=str).fillna("").iloc[0]
        actuacion = pd.read_csv(actuacion_path, dtype=str).fillna("").iloc[0]

        values = {
            "actuacion.id_tipo_actuacion": str(actuacion.get("id_tipo_actuacion", "")).strip(),
            "actuacion.id_instrumento": str(actuacion.get("id_instrumento", "")).strip(),
            "aforo.id_instrumento": str(aforo.get("id_instrumento", "")).strip(),
            "aforo.id_tipo_aforo": str(aforo.get("id_tipo_aforo", "")).strip(),
            "aforo.id_instrumentos_rangos": str(aforo.get("id_instrumentos_rangos", "")).strip(),
        }
        missing = [name for name, value in values.items() if value == ""]
        checks.append({
            "check": f"{row.export_id}:semantic_output_fields",
            "status": "PASS" if not missing else "FAIL",
            "detail": f"values={values}; missing={missing}",
        })

    report = pd.DataFrame(checks)
    report_dir = root / "runs_acceptance" / "_checks"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "sih_semantic_fields_acceptance.csv"
    report.to_csv(report_path, index=False, encoding="utf-8-sig")

    n_pass = int(report["status"].eq("PASS").sum())
    n_fail = int(report["status"].eq("FAIL").sum())

    print("Aforix SIH semantic lookup acceptance")
    print("====================================")
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
