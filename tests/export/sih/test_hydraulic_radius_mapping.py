"""Regression tests: SIH hydraulic radius must come from normalized Summary."""

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest
import yaml

from aforix.export.sih.mappings import build_sdh_aforos_row


CONFIG_PATH = Path(__file__).resolve().parents[3] / "configs" / "sih" / "sih.yaml"


def _export(instrument: str, radius: object, *, raw_radius: str = "99.9") -> dict:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    instrument_cfg = config["sih"]["instruments"][instrument]
    measurement = pd.Series({"hydraulic_radius_m": radius})
    raw_measurement = pd.Series({"radio_hidraulico_m": raw_radius, "rh [m]": raw_radius})
    return build_sdh_aforos_row(
        measurement,
        instrument_cfg,
        datetime(2026, 1, 20, 10, 0, 0),
        "%d/%m/%Y %H:%M:%S",
        id_estacion="7071",
        id_instrumento="1",
        id_tipo_aforo="1",
        id_instrumentos_rangos="1",
        raw_measurement=raw_measurement,
    )


@pytest.mark.parametrize("instrument", ["flowtracker", "molinete", "nivus"])
def test_sih_hydraulic_radius_comes_from_normalized_summary(instrument: str) -> None:
    row = _export(instrument, "0.378638")
    assert row["radio_hidraulico"] == "0.378638"
    assert row["id_estacion"] == "7071"


@pytest.mark.parametrize("instrument", ["flowtracker", "molinete", "nivus"])
@pytest.mark.parametrize("missing", ["", None, pd.NA])
def test_sih_hydraulic_radius_missing_is_blank(instrument: str, missing: object) -> None:
    row = _export(instrument, missing)
    assert row["radio_hidraulico"] == ""


def test_sih_hydraulic_radius_does_not_change_other_fields() -> None:
    row = _export("molinete", "0.42")
    assert row["caudal"] == ""
    assert row["nivel_confiabilidad"] == ""
    assert "incertidumbre_IVE" not in row  # IVE is populated by the separate integration stage.
