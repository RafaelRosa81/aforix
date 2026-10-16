"""Interpolated Variance Estimator helpers.

The formulation follows the Aforix operating method for discrete
velocity-area profiles. Applying it to M9 one-second samples is an explicit
analogy, not a QRev uncertainty calculation.
"""
from __future__ import annotations

from typing import Any

import numpy as np


def calculate_ive_profile(
    distance_m: np.ndarray,
    depth_m: np.ndarray,
    normal_velocity_m_s: np.ndarray,
    *,
    left_bank_distance_m: float = 0.0,
    right_bank_distance_m: float = 0.0,
    minimum_depth_uncertainty_m: float = 0.01,
    systematic_relative_uncertainty: float = 0.01,
    width_relative_uncertainty: float = 0.005,
    minimum_verticals: int = 10,
) -> dict[str, Any]:
    """Calculate the Aforix IVE formulation over an ordered section profile.

    Positive reported bank distances add dry, zero-depth/zero-velocity
    endpoints. The returned Q is the mid-section integration of this profile.
    Velocity uncertainty uses s_v,IVE directly, following the current Aforix
    decision not to apply an instrumental s_v,min floor.
    """
    x = np.asarray(distance_m, dtype=float).reshape(-1)
    d = np.asarray(depth_m, dtype=float).reshape(-1)
    v = np.asarray(normal_velocity_m_s, dtype=float).reshape(-1)
    if not (len(x) == len(d) == len(v)):
        return {"status": "not_available", "reason": "Las series x, d y v tienen distinto largo."}

    # Use exactly the same engine as SIH. Never discard invalid samples or
    # silently merge repeated positions to make an uncertainty calculable.
    from aforix.analysis.uncertainty.calculator import IVEPoint, IVEParameters, calculate_ive

    if len(x) < 2 or not np.all(np.isfinite(x)):
        return {"status": "not_available", "reason": "No hay suficientes posiciones válidas."}
    left = float(left_bank_distance_m)
    right = float(right_bank_distance_m)
    if not np.isfinite(left + right) or min(left, right) < 0:
        return {"status": "not_available", "reason": "Distancias a márgenes inválidas."}
    x = x - np.min(x) + left
    width = float(np.max(x) + right)
    try:
        result = calculate_ive(
            [IVEPoint(float(a), float(b), float(c)) for a, b, c in zip(x, d, v)],
            width,
            IVEParameters(
                systematic_relative=systematic_relative_uncertainty,
                width_relative_per_vertical=width_relative_uncertainty,
                minimum_depth_sd_m=minimum_depth_uncertainty_m,
                left_bank_mode="zero", right_bank_mode="zero",
            ),
        )
    except ValueError as exc:
        return {"status": "not_available", "reason": str(exc)}
    if minimum_verticals != 10:
        raise ValueError("The shared IVE engine requires minimum_verticals=10")
    reason = (
        "IVE no aplicable: menos de 10 verticales/muestras."
        if result.status == "not_applicable"
        else "IVE análogo M9 mediante el motor común de Aforix; no es QRev."
    )
    return {
        "status": result.status, "reason": reason,
        "profile_sample_count": len(x),
        "wet_sample_count": int(np.count_nonzero(d > 0)),
        "q_midsection_m3s": result.q_mid_m3s,
        "s_d_ive_m": result.sd_depth_ive_m,
        "s_d_effective_m": result.sd_depth_used_m,
        "s_v_ive_m_s": result.sd_velocity_ive_m_s,
        "u_s": systematic_relative_uncertainty,
        "u_b_q": result.uncertainty_width_relative,
        "u_d_q": result.uncertainty_depth_relative,
        "u_v_q": result.uncertainty_velocity_relative,
        "relative_uncertainty": (result.relative_uncertainty_pct / 100 if result.relative_uncertainty_pct is not None else None),
        "absolute_error_m3s": result.absolute_uncertainty_m3s,
        "quality": result.quality,
    }
