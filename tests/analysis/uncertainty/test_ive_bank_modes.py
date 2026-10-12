"""Configurable physical bank conditions."""
import pytest

from aforix.analysis.uncertainty.calculator import IVEParameters, IVEPoint, calculate_ive


def _section():
    return [
        IVEPoint(0.0, 0.14, 0.0683),
        *[IVEPoint(float(i), 0.15, 0.1) for i in range(1, 12)],
        IVEPoint(12.0, 0.2, 0.05),
    ]


@pytest.mark.parametrize(
    "mode,depth,velocity",
    [
        ("zero", 0.0, 0.0),
        ("preserve_depth", 0.14, 0.0),
        ("preserve_both", 0.14, 0.0683),
    ],
)
def test_left_bank_modes(mode, depth, velocity):
    result = calculate_ive(
        _section(), 12.0, IVEParameters(left_bank_mode=mode)
    )
    assert result.details[0]["depth_m"] == pytest.approx(depth)
    assert result.details[0]["velocity_m_s"] == pytest.approx(velocity)


@pytest.mark.parametrize(
    "mode,depth,velocity",
    [
        ("zero", 0.0, 0.0),
        ("preserve_depth", 0.2, 0.0),
        ("preserve_both", 0.2, 0.05),
    ],
)
def test_right_bank_modes(mode, depth, velocity):
    result = calculate_ive(
        _section(), 12.0, IVEParameters(right_bank_mode=mode)
    )
    assert result.details[-1]["depth_m"] == pytest.approx(depth)
    assert result.details[-1]["velocity_m_s"] == pytest.approx(velocity)


def test_invalid_bank_mode_rejected():
    with pytest.raises(ValueError, match="Invalid left_bank_mode"):
        calculate_ive(_section(), 12.0, IVEParameters(left_bank_mode="unknown"))


def test_default_bank_modes():
    result = calculate_ive(_section(), 12.0)
    assert result.details[0]["depth_m"] == 0.0
    assert result.details[0]["velocity_m_s"] == 0.0
    assert result.details[-1]["depth_m"] == pytest.approx(0.2)
    assert result.details[-1]["velocity_m_s"] == 0.0
