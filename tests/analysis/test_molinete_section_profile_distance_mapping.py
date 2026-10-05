from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "normalization" / "molinete.yaml"


def test_molinete_points_distance_m_accepts_adapter_progr_m():
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    sources = cfg["groups"]["Points"]["columns"]["distance_m"]["sources"]

    assert "progr_m" in sources, (
        "Molinete adapter emits the cross-section progression as 'progr_m', "
        "so normalized Points.distance_m must include 'progr_m' as a source. "
        f"Configured sources: {sources}"
    )
