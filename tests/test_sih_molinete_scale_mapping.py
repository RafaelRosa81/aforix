from __future__ import annotations

from pathlib import Path

import yaml

from aforix.ingest.adapters.molinete_excel import MolineteExcelAdapter


ROOT = Path(__file__).resolve().parents[1]
CONFIGS = [
    ROOT / "configs" / "sih" / "sih.yaml",
]


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_molinete_scale_fields_use_normalized_summary_columns():
    for path in CONFIGS:
        instrument = _load(path)["sih"]["instruments"]["molinete"]
        normalized_fields = instrument["normalized_fields"]
        raw_fields = instrument["raw_canonical_fields"]

        assert normalized_fields["escala_inicio"] == "escala_inicio", path.name
        assert normalized_fields["escala_fin"] == "escala_fin", path.name
        assert normalized_fields["lectura_escala"] == "escala_inicio", path.name
        assert normalized_fields["id_operador"] == "operador", path.name
        assert raw_fields["escala_inicio"] is None, path.name
        assert raw_fields["escala_fin"] is None, path.name
        assert raw_fields["escala_media"] == "escala_media_m", path.name


def test_molinete_missing_or_dash_final_scale_uses_initial_scale():
    initial = 2.15

    assert MolineteExcelAdapter._resolve_final_scale(initial, None) == initial
    assert MolineteExcelAdapter._resolve_final_scale(
        initial,
        MolineteExcelAdapter._to_float("-"),
    ) == initial
