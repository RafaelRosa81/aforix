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


def test_nivus_measurement_enrichment_preserves_missing_last_point_flow():
    from aforix.normalize.run import _enrich_nivus_points_by_measurement

    keys = {
        "instrument": "nivus",
        "station_id": "7001",
        "measurement_date": "20250711",
        "measurement_time": "151429",
    }
    points = pd.DataFrame([
        {**keys, "point_index": index}
        for index in range(1, 14)
    ])
    sections = pd.DataFrame([
        {
            **keys,
            "section_index": index,
            "width_m": 0.2769 if index not in (1, 2, 14, 15) else 0.2077,
            "depth_m": 0.04,
            "q_ls": "#-1" if index in (14, 15) else 1.0,
            "percent_q": "#-1" if index in (14, 15) else 1.0,
        }
        for index in range(1, 16)
    ])
    result = _enrich_nivus_points_by_measurement(
        points, sections, label="7001_Points_20250711_151429.csv"
    )

    assert len(result) == 13
    assert result.loc[12, "area_m2"] == pytest.approx(2 * 0.2077 * 0.04)
    assert pd.isna(result.loc[12, "q_ls"])
    assert pd.isna(result.loc[12, "q_m3s"])
    assert pd.isna(result.loc[12, "percent_q"])
    assert result.loc[11, "percent_q"] == pytest.approx(1.0)
