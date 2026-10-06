from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
MAIN_CONFIG = ROOT / "configs" / "sih" / "sih.yaml"
TIPOS = ROOT / "configs" / "sih" / "tipos_aforos.csv"
RANGOS = ROOT / "configs" / "sih" / "instrumentos_rangos.csv"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _norm(value: object) -> str:
    return str(value if value is not None else "").strip().casefold()


def _assert_lookup_exists_once(df: pd.DataFrame, key: str, *, label: str) -> None:
    matches = df[df["descripcion"].map(_norm) == _norm(key)]
    assert len(matches) == 1, (
        f"{label}={key!r} must resolve exactly once in lookup; "
        f"matches={len(matches)}; available={df['descripcion'].astype(str).tolist()}"
    )


def test_main_sih_config_semantic_lookup_keys_resolve():
    cfg = _load_yaml(MAIN_CONFIG)["sih"]
    tipos = pd.read_csv(TIPOS, dtype=str).fillna("")
    rangos = pd.read_csv(RANGOS, dtype=str).fillna("")

    for instrument, inst_cfg in cfg["instruments"].items():
        tipo_key = str(inst_cfg.get("tipo_aforo_lookup", "") or "").strip()
        rango_key = str(inst_cfg.get("instrumentos_rangos_lookup", "") or "").strip()

        if tipo_key:
            _assert_lookup_exists_once(
                tipos,
                tipo_key,
                label=f"{instrument}.tipo_aforo_lookup",
            )
        if rango_key:
            _assert_lookup_exists_once(
                rangos,
                rango_key,
                label=f"{instrument}.instrumentos_rangos_lookup",
            )
