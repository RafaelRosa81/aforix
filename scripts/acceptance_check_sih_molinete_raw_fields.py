from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from aforix.export.sih.inputs import (
    load_raw_canonical_summary,
    resolve_measurement,
)


CONFIG = Path("configs/sih/sih_acceptance.yaml")

SELECTION_ROW = pd.Series(
    {
        "station_id": "7071",
        "measurement_date": "20260120",
        "measurement_time": "142300",
        "instrument": "molinete",
        "export_id": "ACCM001",
    }
)

FIELDS = [
    "id_operador",
    "lectura_escala",
    "escala_inicio",
    "escala_fin",
    "escala_media",
    "observaciones",
    "radio_hidraulico",
]


def _show(value: object) -> str:
    if value is None:
        return "<None>"
    text = str(value)
    return "<blank>" if text.strip() == "" else text


def main() -> None:
    root = Path.cwd().resolve()
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    sih = cfg["sih"]
    raw_root = root / sih["inputs"]["raw_canonical_input_dir"]
    inst_cfg = sih["instruments"]["molinete"]
    mapping = inst_cfg["raw_canonical_fields"]

    raw_summary = load_raw_canonical_summary(raw_root, "molinete")
    if raw_summary is None:
        raise SystemExit("Molinete raw-canonical Summary.csv not found.")

    row = resolve_measurement(raw_summary, SELECTION_ROW)

    print("Aforix SIH Molinete raw-field diagnostic")
    print("========================================")
    print("Measurement: station=7071 date=20260120 time=142300")
    print("")
    print("Configured SIH field -> raw column -> raw value")

    checks = []
    for sih_field in FIELDS:
        source_column = mapping.get(sih_field)
        exists = bool(source_column) and source_column in row.index
        value = row.get(source_column, "") if exists else ""
        checks.append(
            {
                "sih_field": sih_field,
                "configured_source": source_column or "",
                "source_column_exists": exists,
                "raw_value": _show(value),
            }
        )
        print(
            f"{sih_field}: {source_column!r} -> "
            f"exists={exists} -> {_show(value)}"
        )

    # Show the actual adapter-scale columns side by side, independent of config.
    print("")
    print("Raw canonical scale columns present in selected row:")
    for col in ["esc_ini_m", "esc_fin_m", "escala_media_m", "escala_media"]:
        print(
            f"{col}: exists={col in row.index} -> "
            f"{_show(row.get(col, '')) if col in row.index else '<missing column>'}"
        )

    report = pd.DataFrame(checks)
    report_dir = root / "runs_acceptance" / "_checks"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "sih_molinete_raw_fields_acceptance.csv"
    report.to_csv(report_path, index=False, encoding="utf-8-sig")

    print("")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
