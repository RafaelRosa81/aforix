from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from aforix.export.sih.inputs import (
    load_normalized_summary,
    load_raw_canonical_summary,
    resolve_optional_measurement,
)


CONFIG = Path("configs/sih/sih_acceptance.yaml")
OUTPUT = Path("runs_acceptance/_checks/sih_nivus_selection.csv")
EXPORT_ID = "ACCN001"


def _norm_date(value: object) -> str:
    return str(value).replace("-", "").strip()


def _norm_time(value: object) -> str:
    return str(value).replace(":", "").replace(".", "").strip()[:6].zfill(6)


def main() -> None:
    root = Path.cwd().resolve()
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["sih"]

    normalized_root = root / cfg["inputs"]["normalized_input_dir"]
    raw_root = root / cfg["inputs"]["raw_canonical_input_dir"]

    summary = load_normalized_summary(normalized_root, "nivus").copy()
    raw = load_raw_canonical_summary(raw_root, "nivus")

    if summary.empty:
        raise SystemExit("No Nivus rows found in normalized Summary.")

    required_numeric = [
        "q_total_m3s",
        "width_total_m",
        "depth_mean_m",
        "area_total_m2",
        "velocity_mean_m_s",
    ]
    for col in required_numeric:
        if col not in summary.columns:
            raise SystemExit(f"Missing normalized Nivus column: {col}")
        summary[col] = pd.to_numeric(summary[col], errors="coerce")

    candidates = summary.dropna(subset=required_numeric).copy()
    positive = candidates[candidates["q_total_m3s"] > 0].copy()
    if not positive.empty:
        candidates = positive

    candidates["_date"] = candidates["measurement_date"].map(_norm_date)
    candidates["_time"] = candidates["measurement_time"].map(_norm_time)
    candidates["_station"] = candidates["station_id"].astype(str)
    candidates = candidates.sort_values(["_station", "_date", "_time"], kind="stable")

    selected = None
    selected_raw = None
    for _, row in candidates.iterrows():
        selection_row = pd.Series({
            "station_id": str(row["station_id"]),
            "measurement_date": _norm_date(row["measurement_date"]),
            "measurement_time": _norm_time(row["measurement_time"]),
            "instrument": "nivus",
            "export_id": EXPORT_ID,
        })
        raw_row = resolve_optional_measurement(raw, selection_row)
        if raw_row is not None:
            selected = selection_row
            selected_raw = raw_row
            break

    if selected is None:
        raise SystemExit("No Nivus candidate with matching raw-canonical Summary row was found.")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([selected.to_dict()]).to_csv(
        OUTPUT, index=False, encoding="utf-8-sig"
    )

    normalized_row = candidates[
        (candidates["_station"] == selected["station_id"])
        & (candidates["_date"] == selected["measurement_date"])
        & (candidates["_time"] == selected["measurement_time"])
    ].iloc[0]

    print("Aforix SIH Nivus acceptance case")
    print("================================")
    print(f"Selection file: {root / OUTPUT}")
    print(f"station_id: {selected['station_id']}")
    print(f"measurement_date: {selected['measurement_date']}")
    print(f"measurement_time: {selected['measurement_time']}")
    print(f"export_id: {EXPORT_ID}")
    print("")
    print("Normalized hydraulic values:")
    for col in required_numeric:
        print(f"  {col}: {normalized_row[col]}")
    print("")
    print("Raw-canonical context:")
    for col in ["instrument", "notes", "rh [m]"]:
        exists = col in selected_raw.index
        value = selected_raw.get(col, "") if exists else ""
        print(f"  {col}: exists={exists}; value={value!r}")


if __name__ == "__main__":
    main()
