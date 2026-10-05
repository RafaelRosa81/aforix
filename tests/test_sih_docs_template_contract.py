from __future__ import annotations

from pathlib import Path
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def test_selection_template_uses_authoritative_station_ids():
    path = ROOT / "configs" / "sih" / "selection_template.csv"
    df = pd.read_csv(path, dtype=str).fillna("")

    assert not df["station_id"].str.match(r"(?i)^p\d+$").any(), (
        "selection_template.csv must use authoritative station_id values directly; "
        "legacy P-prefixed aliases are not allowed"
    )


def test_sih_configuration_docs_match_current_adopted_mappings():
    text = (ROOT / "docs" / "SIH_CONFIGURATION.md").read_text(encoding="utf-8")

    stale_fragments = [
        "tipo_aforo_lookup: Vadeo",
        "tipo_aforo_lookup: Acustico",
        "Velocimetro puntual",
        "Doppler acustico",
        "ADCP movil",
        "lectura_escala: escala_media\n",
        "escala_media: escala_media\n",
    ]
    stale = [fragment for fragment in stale_fragments if fragment in text]

    assert not stale, f"stale SIH configuration documentation fragments: {stale}"

    required_fragments = [
        "VADEO",
        "BOTE",
        "Velocimetro",
        "Acustico",
        "ADCP",
        "lectura_escala: escala_media_m",
        "escala_media: escala_media_m",
    ]
    missing = [fragment for fragment in required_fragments if fragment not in text]

    assert not missing, f"current SIH configuration documentation missing: {missing}"


def test_sih_export_examples_do_not_use_legacy_p_station_aliases():
    text = (ROOT / "docs" / "SIH_EXPORT.md").read_text(encoding="utf-8")

    patterns = [
        r"station_id=P\d+",
        r"\[[0-9]+\]\s+P\d+",
        r"_P\d+_",
        r"Estaciones:\s*P\d+",
    ]
    hits = [pattern for pattern in patterns if re.search(pattern, text, flags=re.IGNORECASE)]

    assert not hits, (
        "SIH_EXPORT.md examples must use authoritative station IDs without "
        f"legacy P aliases; matched patterns: {hits}"
    )
