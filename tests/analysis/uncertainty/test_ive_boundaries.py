"""Tests for physical boundaries in the IVE mid-section calculation.

Copy to tests/analysis/uncertainty/test_ive_boundaries.py.
"""
import pytest
from aforix.analysis.uncertainty.calculator import IVEPoint, calculate_ive


def _section(include_left=True, include_right=True, left_depth=0.05):
    points = [IVEPoint(i * 0.2, 0.12, 0.2) for i in range(1, 13)]
    if include_left:
        points.insert(0, IVEPoint(0.0, left_depth, 0.0))
    if include_right:
        points.append(IVEPoint(2.6, 0.0, 0.0))
    return points


def test_positive_depth_left_bank_is_not_measured_vertical():
    result = calculate_ive(_section(), width_m=2.6)
    assert result.vertical_count == 12
    assert result.status == 'calculated'


@pytest.mark.parametrize('left,right', [(False, True), (True, False), (False, False)])
def test_missing_banks_are_inserted_without_changing_interior_count(left, right):
    result = calculate_ive(_section(include_left=left, include_right=right), width_m=2.6)
    assert result.vertical_count == 12
    assert result.status == 'calculated'


def test_added_zero_depth_bank_preserves_mid_section_discharge():
    full = calculate_ive(_section(left_depth=0), width_m=2.6)
    missing = calculate_ive(_section(include_left=False), width_m=2.6)
    assert missing.q_mid_m3s == pytest.approx(full.q_mid_m3s, abs=1e-12)
