import pytest

from aforix.analysis.uncertainty.ive import (
    IVEStatus,
    IVE_TOO_FEW_VERTICALS,
    check_ive_applicability,
    classify_ive,
)


@pytest.mark.parametrize(
    "uncertainty,expected",
    [
        (0.0, "Excelente"),
        (2.0, "Excelente"),
        (2.01, "Buena"),
        (5.0, "Buena"),
        (5.01, "Regular"),
        (8.0, "Regular"),
        (8.01, "Mala"),
        (10.2, "Mala"),
    ],
)
def test_ive_quality(uncertainty, expected):
    assert classify_ive(uncertainty) == expected


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf")])
def test_ive_rejects_invalid_uncertainty(value):
    with pytest.raises(ValueError):
        classify_ive(value)


@pytest.mark.parametrize("count", [0, 1, 9])
def test_ive_not_applicable_below_ten_verticals(count):
    result = check_ive_applicability(count)
    assert result.status == IVEStatus.NOT_APPLICABLE
    assert result.relative_uncertainty_pct is None
    assert result.absolute_uncertainty_m3s is None
    assert result.quality == IVE_TOO_FEW_VERTICALS


def test_ive_applicability_at_ten_verticals():
    assert check_ive_applicability(10) is None
