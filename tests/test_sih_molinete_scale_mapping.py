from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONFIGS = [
    ROOT / "configs" / "sih" / "sih.yaml",
]


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_molinete_scale_fields_use_adapter_raw_column_names():
    for path in CONFIGS:
        raw_fields = _load(path)["sih"]["instruments"]["molinete"]["raw_canonical_fields"]

        assert raw_fields["escala_inicio"] == "esc_ini_m", path.name
        assert raw_fields["escala_fin"] == "esc_fin_m", path.name
        assert raw_fields["escala_media"] == "escala_media_m", path.name
        assert raw_fields["lectura_escala"] == "escala_media_m", path.name
