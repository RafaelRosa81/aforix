from __future__ import annotations

from typing import Any, List

from aforix.analysis.correlation.types import MeasuringInstrument


def load_instruments(cfg: dict[str, Any]) -> List[MeasuringInstrument]:
    raw = cfg.get("measuring_instruments", [])

    instruments: List[MeasuringInstrument] = []
    for item in raw:
        if not isinstance(item, dict):
            continue

        code = str(item.get("code", "")).upper().strip()
        name = str(item.get("name", "")).strip()
        subdir = str(item.get("subdir", "")).strip()

        if not code or not subdir:
            continue

        instruments.append(
            MeasuringInstrument(
                code=code,
                name=name,
                subdir=subdir,
                summary_format=item.get("summary_format", "wide"),
                flow_column=item.get("flow_column"),
                flow_unit=item.get("flow_unit", "l/s"),
                flow_row_label=item.get("flow_row_label"),
                time_row_label=item.get("time_row_label"),
            )
        )

    if not instruments:
        raise ValueError("No measuring_instruments defined in config.")

    return instruments
