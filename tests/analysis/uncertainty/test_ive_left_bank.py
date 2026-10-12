"""Regression tests for the agreed IVE left-bank convention."""
import pytest

from aforix.analysis.uncertainty.calculator import IVEPoint, calculate_ive


def _points(left_depth: float, left_velocity: float):
    return [
        IVEPoint(0.0, left_depth, left_velocity),
        *[
            IVEPoint(float(i), 0.5 + i * 0.01, 0.2 + i * 0.005)
            for i in range(1, 12)
        ],
        IVEPoint(12.0, 0.0, 0.0),
    ]


def test_left_bank_positive_source_values_are_imposed_zero():
    source = _points(0.14, 0.0683)
    result = calculate_ive(source, width_m=12.0)
    baseline = calculate_ive(_points(0.0, 0.0), width_m=9.0)

    assert source[0].depth_m == pytest.approx(0.14)
    assert source[0].velocity_m_s == pytest.approx(0.0683)
    assert result.details[0]["depth_m"] == 0.0
    assert result.details[0]["velocity_m_s"] == 0.0
    assert result.q_mid_m3s == pytest.approx(baseline.q_mid_m3s)
    assert result.relative_uncertainty_pct == pytest.approx(
        baseline.relative_uncertainty_pct
    )


def test_missing_left_bank_is_inserted_at_zero():
    result = calculate_ive(_points(0.14, 0.0683)[1:], width_m=9.0)
    assert result.details[0]["distance_m"] == 0.0
    assert result.details[0]["depth_m"] == 0.0
    assert result.details[0]["velocity_m_s"] == 0.0
