from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


MIN_IVE_VERTICALS = 10
IVE_TOO_FEW_VERTICALS = "IVE no aplicable: menos de 10 verticales"


class IVEStatus(str, Enum):
    CALCULATED = "calculated"
    NOT_APPLICABLE = "not_applicable"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass(frozen=True)
class IVEResult:
    status: IVEStatus
    vertical_count: int
    relative_uncertainty_pct: float | None = None
    absolute_uncertainty_m3s: float | None = None
    quality: str | None = None
    reason: str | None = None


def classify_ive(relative_uncertainty_pct: float) -> str:
    """Classify IVE relative uncertainty expressed as percent."""
    import math

    value = float(relative_uncertainty_pct)

    if not math.isfinite(value) or value < 0:
        raise ValueError("IVE uncertainty must be finite and nonnegative.")

    if value <= 2:
        return "Excelente"
    if value <= 5:
        return "Buena"
    if value <= 8:
        return "Regular"
    return "Mala"


def check_ive_applicability(vertical_count: int) -> IVEResult | None:
    """Return an inapplicable result, or None if IVE can be evaluated."""
    if isinstance(vertical_count, bool) or not isinstance(vertical_count, int):
        raise TypeError("vertical_count must be an integer.")
    if vertical_count < 0:
        raise ValueError("vertical_count cannot be negative.")

    if vertical_count < MIN_IVE_VERTICALS:
        return IVEResult(
            status=IVEStatus.NOT_APPLICABLE,
            vertical_count=vertical_count,
            quality=IVE_TOO_FEW_VERTICALS,
            reason=IVE_TOO_FEW_VERTICALS,
        )

    return None
