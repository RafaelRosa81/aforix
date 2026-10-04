from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from aforix.export.sih.inputs import load_normalized_summary, resolve_measurement


CONFIG = Path("configs/sih/sih_acceptance.yaml")
SELECTION = Path("runs_acceptance/_checks/sih_nivus_selection.csv")


def _clean(value: object) -> str:
    return str(value if value is not None else "").strip()


def _float_equal(a: object, b: object, tol: float = 1e-9) -> bool:
    try:
        av = float(a)
        bv = float(b)
    except (TypeError, ValueError):
        return False
    return abs(av - bv) <= tol * max(1.0, abs(av), abs(bv))


def main() -> None:
    root = Path.cwd().resolve()
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["sih"]
    selection = pd.read_csv(SELECTION, dtype=str).fillna("")
    if len(selection) != 1:
        raise SystemExit(f"Expected exactly 1 Nivus selection row, got {len(selection)}")
    row = selection.iloc[0]

    output_dir = root / cfg["output"]["output_dir"]
    suffix = f"{row['station_id']}_{row['measurement_date']}_{row['measurement_time']}"
    aforo_path = output_dir / f"ID_{row['export_id']}_aforo_{suffix}.csv"
    actuacion_path = output_dir / f"ID_{row['export_id']}_actuacion_{suffix}.csv"
    metadata_path = output_dir / "sih_export_metadata.csv"

    checks: list[dict[str, str]] = []

    files_ok = aforo_path.exists() and actuacion_path.exists() and metadata_path.exists()
    checks.append({
        "check": "expected_files",
        "status": "PASS" if files_ok else "FAIL",
        "detail": f"aforo={aforo_path.exists()}, actuacion={actuacion_path.exists()}, metadata={metadata_path.exists()}",
    })

    if files_ok:
        aforo = pd.read_csv(aforo_path, dtype=str).fillna("").iloc[0]
        actuacion = pd.read_csv(actuacion_path, dtype=str).fillna("").iloc[0]
        metadata = pd.read_csv(metadata_path, dtype=str).fillna("")
        meta = metadata[metadata["export_id"] == row["export_id"]]

        metadata_ok = (
            len(meta) == 1
            and _clean(meta.iloc[0].get("status")) == "success"
            and _clean(meta.iloc[0].get("station_id")) == row["station_id"]
            and _clean(meta.iloc[0].get("measurement_date")).replace("-", "") == row["measurement_date"]
            and _clean(meta.iloc[0].get("measurement_time")).replace(":", "")[:6] == row["measurement_time"]
        )
        checks.append({
            "check": "metadata_success_identity",
            "status": "PASS" if metadata_ok else "FAIL",
            "detail": meta.iloc[0].to_dict() if len(meta) == 1 else f"matches={len(meta)}",
        })

        observed_ids = {
            "id_tipo_actuacion": _clean(actuacion.get("id_tipo_actuacion")),
            "id_instrumento": _clean(aforo.get("id_instrumento")),
            "id_tipo_aforo": _clean(aforo.get("id_tipo_aforo")),
            "id_instrumentos_rangos": _clean(aforo.get("id_instrumentos_rangos")),
            "id_estacion": _clean(aforo.get("id_estacion")),
        }
        expected_ids = {
            "id_tipo_actuacion": "4",
            "id_instrumento": "502",
            "id_tipo_aforo": "57",
            "id_instrumentos_rangos": "10",
            "id_estacion": row["station_id"],
        }
        checks.append({
            "check": "expected_semantic_ids",
            "status": "PASS" if observed_ids == expected_ids else "FAIL",
            "detail": f"observed={observed_ids}; expected={expected_ids}",
        })

        normalized_root = root / cfg["inputs"]["normalized_input_dir"]
        normalized = load_normalized_summary(normalized_root, "nivus")
        source = resolve_measurement(normalized, row)

        mappings = {
            "ancho": "width_total_m",
            "caudal": "q_total_m3s",
            "profundidad": "depth_mean_m",
            "seccion": "area_total_m2",
            "velocidad_media": "velocity_mean_m_s",
        }
        bad = {}
        for out_col, source_col in mappings.items():
            if not _float_equal(aforo.get(out_col, ""), source.get(source_col, "")):
                bad[out_col] = {
                    "exported": _clean(aforo.get(out_col, "")),
                    "normalized": _clean(source.get(source_col, "")),
                }

        checks.append({
            "check": "hydraulic_numeric_fidelity",
            "status": "PASS" if not bad else "FAIL",
            "detail": "all matched" if not bad else str(bad),
        })

        # Current SIH quality integration is intentionally not asserted here.
        # The config declares Nivus quality thresholds, but production mapping
        # does not yet populate nivel_confiabilidad.
        checks.append({
            "check": "nivel_confiabilidad_observed",
            "status": "INFO",
            "detail": f"value={_clean(aforo.get('nivel_confiabilidad', ''))!r}",
        })
    else:
        for name in [
            "metadata_success_identity",
            "expected_semantic_ids",
            "hydraulic_numeric_fidelity",
        ]:
            checks.append({"check": name, "status": "FAIL", "detail": "required output unavailable"})
        checks.append({"check": "nivel_confiabilidad_observed", "status": "INFO", "detail": "required output unavailable"})

    report = pd.DataFrame(checks)
    report_dir = root / "runs_acceptance" / "_checks"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "sih_nivus_acceptance.csv"
    report.to_csv(report_path, index=False, encoding="utf-8-sig")

    n_pass = int(report["status"].eq("PASS").sum())
    n_fail = int(report["status"].eq("FAIL").sum())
    n_info = int(report["status"].eq("INFO").sum())

    print("Aforix SIH Nivus acceptance")
    print("===========================")
    print(f"Checks: {len(report)}")
    print(f"PASS: {n_pass}")
    print(f"FAIL: {n_fail}")
    print(f"INFO: {n_info}")
    print(f"Report: {report_path}")
    print("")
    print(report.to_string(index=False))

    if n_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
