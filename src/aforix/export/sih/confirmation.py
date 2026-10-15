from __future__ import annotations

from collections import Counter
from typing import Any, Callable

import pandas as pd


def _display(value: Any) -> str:
    return "No configurado" if value is None else str(value)


def _display_border(value: Any) -> str:
    return {"zero": "Profundidad cero", "preserve_depth": "Conservar profundidad"}.get(str(value), _display(value))


def confirm_instrument_configurations(
    sih_config: dict[str, Any],
    selection: pd.DataFrame,
    *,
    assume_yes: bool = False,
    ask: Callable[[str], str] = input,
) -> bool:
    """Confirm effective SIH settings once per selected instrument, before export.

    Returns False on refusal or unavailable stdin; caller must not run export.
    """
    counts = Counter(str(value).strip().lower() for value in selection["instrument"])
    instruments = sih_config["sih"].get("instruments", {})
    borders = sih_config["sih"].get("ive", {}).get("borders", {})
    left = borders.get("left", "zero")
    right = borders.get("right", "preserve_depth")

    # Validate all selected instrument configurations before asking or exporting.
    for instrument in counts:
        if instrument not in instruments or not instruments[instrument].get("enabled", True):
            raise ValueError(f"Instrumento SIH no habilitado o desconocido: {instrument}")

    for instrument in sorted(counts):
        cfg = instruments[instrument]
        lookup = cfg.get("instrument_lookup_fields", {})
        print("\nAFORIX — CONFIRMACIÓN DE EXPORTACIÓN AL SIH")
        print("=" * 43)
        print(f"Instrumento: {instrument.upper()}")
        print(f"Aforos seleccionados: {counts[instrument]}")
        print("\nDATOS DE LA ACTUACIÓN Y DEL AFORO")
        for key, label in (("id_tipo_actuacion", "Tipo de actuación (ID)"), ("tipo_aforo_lookup", "Tipo de aforo"), ("instrumentos_rangos_lookup", "Rango del instrumento")):
            print(f"  {label}: {_display(cfg.get(key))}")
        print("\nIDENTIFICACIÓN DEL INSTRUMENTO")
        for key, label in (("marca", "Marca"), ("nro_serie", "Número de serie"), ("modelo", "Modelo"), ("codigo", "Código")):
            print(f"  {label}: {_display(lookup.get(key))}")
        print("\nCÁLCULO DE INCERTIDUMBRE (IVE)")
        print(f"  Margen izquierdo: {_display_border(left)}")
        print(f"  Margen derecho: {_display_border(right)}")

        if assume_yes:
            print("Confirmación automática: --yes")
            continue

        try:
            answer = ask(f"¿Confirma esta configuración para {instrument.upper()}? [s/N]: ")
        except (EOFError, KeyboardInterrupt, OSError):
            print("\nExportación cancelada: no se obtuvo confirmación.")
            return False
        if answer.strip().lower() not in {"s", "si", "sí", "y", "yes"}:
            print("Exportación cancelada: configuración no confirmada.")
            return False

    return True
