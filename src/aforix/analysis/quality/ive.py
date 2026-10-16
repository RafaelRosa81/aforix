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

    valid = np.isfinite(x) & np.isfinite(d) & np.isfinite(v) & (d >= 0)
    x, d, v = x[valid], d[valid], v[valid]
    if len(x) < 2:
        return {"status": "not_available", "reason": "No hay suficientes muestras válidas del perfil."}
    order = np.argsort(x, kind="stable")
    x, d, v = x[order], d[order], v[order]
    unique = np.concatenate(([True], np.diff(x) > 1e-9))
    x, d, v = x[unique], d[unique], v[unique]
    if len(x) < 2:
        return {"status": "not_available", "reason": "El perfil no tiene posiciones distintas."}

    left = max(0.0, float(left_bank_distance_m or 0.0))
    right = max(0.0, float(right_bank_distance_m or 0.0))
    if left > 0:
        x = np.r_[x[0] - left, x]
        d = np.r_[0.0, d]
        v = np.r_[0.0, v]
    if right > 0:
        x = np.r_[x, x[-1] + right]
        d = np.r_[d, 0.0]
        v = np.r_[v, 0.0]

    n = len(x)
    if n < minimum_verticals:
        return {
            "status": "not_applicable",
            "reason": f"IVE no aplicable: menos de {minimum_verticals} verticales/muestras.",
            "profile_sample_count": n,
        }
    dx = np.diff(x)
    if np.any(dx <= 0):
        return {"status": "not_available", "reason": "La progresiva del perfil no es estrictamente creciente."}

    widths = np.empty(n, dtype=float)
    widths[0] = dx[0] / 2.0
    widths[-1] = dx[-1] / 2.0
    widths[1:-1] = (x[2:] - x[:-2]) / 2.0
    q_i = widths * d * v
    q_mid = float(q_i.sum())
    if not np.isfinite(q_mid) or abs(q_mid) <= 1e-12:
        return {"status": "not_available", "reason": "El caudal mid-section del perfil es cero o no finito."}

    # Residuals for i=3,...,N-2 (one-based), with N-5 degrees of freedom.
    idx = np.arange(2, n - 2)
    omega = (x[idx + 1] - x[idx]) / (x[idx + 1] - x[idx - 1])
    variance_factor = 2.0 * (1.0 - omega + omega**2)
    d_hat = omega * d[idx - 1] + (1.0 - omega) * d[idx + 1]
    v_hat = omega * v[idx - 1] + (1.0 - omega) * v[idx + 1]
    s_d_ive = float(np.sqrt(np.sum((d[idx] - d_hat) ** 2 / variance_factor) / (n - 5)))
    s_v_ive = float(np.sqrt(np.sum((v[idx] - v_hat) ** 2 / variance_factor) / (n - 5)))
    s_d = max(s_d_ive, float(minimum_depth_uncertainty_m))
    s_v = s_v_ive

    u_b = float(np.sqrt(np.sum((q_i * width_relative_uncertainty) ** 2)) / abs(q_mid))
    u_d = float(np.sqrt(np.sum((widths * v * s_d) ** 2)) / abs(q_mid))
    u_v = float(np.sqrt(np.sum((widths * d * s_v) ** 2)) / abs(q_mid))
    u_s = float(systematic_relative_uncertainty)
    u_r_q = float(np.sqrt(u_s**2 + u_b**2 + u_d**2 + u_v**2))
    u_q = abs(q_mid) * u_r_q
    ive_pct = 100.0 * u_r_q
    quality = "Excelente" if ive_pct <= 2 else "Buena" if ive_pct <= 5 else "Regular" if ive_pct <= 8 else "Mala"
    return {
        "status": "calculated",
        "reason": "IVE análogo aplicado a muestras M9 de perfiles verticales de 1 s; no es el cálculo QRev.",
        "profile_sample_count": n,
        "wet_sample_count": int(np.count_nonzero(d > 0)),
        "q_midsection_m3s": q_mid,
        "s_d_ive_m": s_d_ive,
        "s_d_effective_m": s_d,
        "s_v_ive_m_s": s_v_ive,
        "u_s": u_s,
        "u_b_q": u_b,
        "u_d_q": u_d,
        "u_v_q": u_v,
        "relative_uncertainty": u_r_q,
        "absolute_error_m3s": u_q,
        "quality": quality,
    }
