import pandas as pd
import pytest

from aforix.normalize.run import _enrich_nivus_points_from_sections


def test_nivus_missing_section_flow_keeps_geometry_and_unknown_flow():
    points = pd.DataFrame({"point_index": [1, 2]})
    sections = pd.DataFrame({
        "section_index": [1, 2, 3, 4],
        "width_m": [0.2, 0.3, 0.4, 0.1],
        "depth_m": [0.1, 0.2, 0.3, 0.04],
        "q_ls": [1.0, 2.0, 3.0, "#-1"],
        "percent_q": [10.0, 20.0, 30.0, "#-1"],
    })
    out = _enrich_nivus_points_from_sections(points, sections, label="nivus-test")

    assert out.loc[0, "area_m2"] == pytest.approx(0.08)
    assert out.loc[0, "q_ls"] == pytest.approx(3.0)
    assert out.loc[0, "percent_q"] == pytest.approx(30.0)
    assert out.loc[1, "area_m2"] == pytest.approx(0.124)
    assert pd.isna(out.loc[1, "q_ls"])
    assert pd.isna(out.loc[1, "q_m3s"])
    assert pd.isna(out.loc[1, "percent_q"])


def test_nivus_missing_section_geometry_still_fails():
    points = pd.DataFrame({"point_index": [1]})
    sections = pd.DataFrame({
        "section_index": [1, 2, 3],
        "width_m": [0.2, 0.3, 0.1],
        "depth_m": [0.1, "#-1", 0.04],
        "q_ls": [1.0, 2.0, 3.0],
        "percent_q": [10.0, 20.0, 30.0],
    })
    with pytest.raises(ValueError, match="missing geometry"):
        _enrich_nivus_points_from_sections(points, sections, label="nivus-test")
