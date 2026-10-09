import numpy as np
import pandas as pd
import pytest

from aforix.normalize.run import (
    _enrich_nivus_points_from_sections,
    _enrich_nivus_points_by_measurement,
    _validate_zero_flow_summary,
)


def fixture(flow=0.0):
    metadata = dict(instrument="nivus", station_id="7006",
                    measurement_date="20241130", measurement_time="145239")
    points = pd.DataFrame([dict(metadata, point_index=i, velocity_mean_m_s=0.0,
                                percent_q=np.nan) for i in (1, 2)])
    sections = pd.DataFrame([dict(metadata, section_index=i, width_m=0.2,
                                  depth_m=0.5, q_ls=flow, percent_q=np.nan)
                             for i in (1, 2, 3, 4)])
    return points, sections


def test_zero_flow_keeps_geometry_and_flow_with_undefined_shares():
    points, sections = fixture()
    result = _enrich_nivus_points_by_measurement(points, sections, label="zero")
    assert result.percent_q.isna().all()
    assert result.q_ls.eq(0.0).all()
    assert result.q_m3s.eq(0.0).all()
    assert result.area_m2.tolist() == pytest.approx([0.2, 0.2])


@pytest.mark.parametrize("bad_column", ["width_m", "depth_m", "q_ls"])
def test_zero_flow_does_not_hide_missing_hydraulic_data(bad_column):
    points, sections = fixture()
    sections.loc[0, bad_column] = np.nan
    with pytest.raises(ValueError):
        _enrich_nivus_points_from_sections(points, sections, label="bad")


def test_nonzero_flow_still_requires_shares():
    points, sections = fixture(1.0)
    with pytest.raises(ValueError, match="percent_q"):
        _enrich_nivus_points_by_measurement(points, sections, label="nonzero")


def test_mixed_measurements_do_not_share_zero_flow_exemption():
    zero_points, zero_sections = fixture()
    moving_points, moving_sections = fixture(1.0)
    moving_points.station_id = "OTHER"
    moving_sections.station_id = "OTHER"
    with pytest.raises(ValueError, match="percent_q"):
        _enrich_nivus_points_by_measurement(
            pd.concat([zero_points, moving_points], ignore_index=True),
            pd.concat([zero_sections, moving_sections], ignore_index=True), label="mixed",
        )


@pytest.mark.parametrize("total", [0.0, 1.0, np.nan])
def test_undefined_share_requires_zero_summary(total):
    points, sections = fixture()
    result = _enrich_nivus_points_by_measurement(points, sections, label="zero")
    summary = points.iloc[[0]].copy()
    summary["q_total_ls"] = total
    if total == 0.0:
        _validate_zero_flow_summary(result, summary)
    else:
        with pytest.raises(ValueError, match="zero-flow Summary"):
            _validate_zero_flow_summary(result, summary)
