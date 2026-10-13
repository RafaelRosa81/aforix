from __future__ import annotations

from dataclasses import dataclass
from math import isclose, isfinite, sqrt
from typing import Sequence

from .ive import check_ive_applicability, classify_ive


@dataclass(frozen=True)
class IVEParameters:
    systematic_relative: float = 0.01
    width_relative_per_vertical: float = 0.005
    minimum_depth_sd_m: float = 0.01
    left_bank_mode: str = "zero"
    right_bank_mode: str = "preserve_depth"


@dataclass(frozen=True)
class IVEPoint:
    distance_m: float
    depth_m: float
    velocity_m_s: float


@dataclass(frozen=True)
class IVECalculation:
    status: str
    vertical_count: int
    q_mid_m3s: float
    relative_uncertainty_pct: float | None
    absolute_uncertainty_m3s: float | None
    quality: str
    sd_depth_ive_m: float | None
    sd_velocity_ive_m_s: float | None
    sd_depth_used_m: float | None
    sd_velocity_used_m_s: float | None
    uncertainty_width_relative: float | None
    uncertainty_depth_relative: float | None
    uncertainty_velocity_relative: float | None
    details: tuple[dict, ...]


def calculate_ive(
    points: Sequence[IVEPoint],
    width_m: float,
    parameters: IVEParameters | None = None,
) -> IVECalculation:
    """Calculate IVE uncertainty using the reviewed mid-section template."""
    p = parameters or IVEParameters()

    valid_bank_modes = {"zero", "preserve_depth", "preserve_both"}
    for side in ("left_bank_mode", "right_bank_mode"):
        if getattr(p, side) not in valid_bank_modes:
            raise ValueError(f"Invalid {side}: {getattr(p, side)!r}; expected {sorted(valid_bank_modes)}")

    for name, value in vars(p).items():
        if isinstance(value, str) or value is None:
            continue
        if not isfinite(value) or value < 0:
            raise ValueError(f"Invalid IVE parameter: {name}")

    if not isfinite(width_m) or width_m <= 0:
        raise ValueError("width_m must be positive and finite")

    nodes = sorted(points, key=lambda point: point.distance_m)

    if len(nodes) < 2:
        raise ValueError("At least two section points are required")

    for point in nodes:
        if not all(isfinite(v) for v in vars(point).values()):
            raise ValueError("Non-finite point value")
        if point.depth_m < 0:
            raise ValueError("Negative depth")
        if point.distance_m < 0 or point.distance_m > width_m:
            raise ValueError("Point outside section")

    x = [point.distance_m for point in nodes]
    d = [point.depth_m for point in nodes]
    v = [point.velocity_m_s for point in nodes]

    if any(b <= a for a, b in zip(x, x[1:])):
        raise ValueError("Positions must be strictly increasing")

    # Incorporate missing physical banks without modifying original points.
    if not isclose(x[0], 0.0, abs_tol=1e-8):
        x.insert(0, 0.0)
        d.insert(0, 0.0)
        v.insert(0, 0.0)

    if not isclose(x[-1], width_m, abs_tol=1e-8):
        x.append(width_m)
        d.append(0.0)
        v.append(0.0)

    # Subsequent calculations must include the inserted boundary nodes.
    nodes = [
        IVEPoint(distance_m=xi, depth_m=di, velocity_m_s=vi)
        for xi, di, vi in zip(x, d, v)
    ]

    # Apply configured boundary conditions without modifying source points.
    # Synthetic banks are always zero; preserve modes affect existing records only.
    for idx, mode in ((0, p.left_bank_mode), (-1, p.right_bank_mode)):
        if mode == "zero":
            d[idx] = 0.0
            v[idx] = 0.0
        elif mode == "preserve_depth":
            v[idx] = 0.0
        # preserve_both retains the original depth and velocity.


    widths = []
    q_values = []

    for i in range(len(nodes)):
        left = 0.0 if i == 0 else (x[i - 1] + x[i]) / 2
        right = width_m if i == len(nodes) - 1 else (x[i] + x[i + 1]) / 2
        w = right - left
        widths.append(w)
        q_values.append(w * d[i] * v[i])

    q_mid = sum(q_values)

    # Both physical boundaries are excluded, even if depth is positive.
    n = len(nodes) - 2
    applicability = check_ive_applicability(n)

    if applicability is not None:
        return IVECalculation(
            status="not_applicable",
            vertical_count=n,
            q_mid_m3s=q_mid,
            relative_uncertainty_pct=None,
            absolute_uncertainty_m3s=None,
            quality=applicability.quality,
            sd_depth_ive_m=None,
            sd_velocity_ive_m_s=None,
            sd_depth_used_m=None,
            sd_velocity_used_m_s=None,
            uncertainty_width_relative=None,
            uncertainty_depth_relative=None,
            uncertainty_velocity_relative=None,
            details=(),
        )

    sum_depth_residual = 0.0
    sum_velocity_residual = 0.0
    rows = []

    for i in range(len(nodes)):
        order = i  # Interior orders are 1 through N.
        include_residual = 3 <= order <= n - 2

        row = {
            "index": i,
            "distance_m": x[i],
            "depth_m": d[i],
            "velocity_m_s": v[i],
            "width_mid_m": widths[i],
            "q_mid_m3s": q_values[i],
            "interior": 0 < i < len(nodes) - 1,
            "ive_residual": include_residual,
        }

        if include_residual:
            omega = (x[i + 1] - x[i]) / (x[i + 1] - x[i - 1])
            depth_estimated = omega * d[i - 1] + (1 - omega) * d[i + 1]
            velocity_estimated = omega * v[i - 1] + (1 - omega) * v[i + 1]
            factor = 2 * (1 - omega + omega**2)

            depth_residual = (d[i] - depth_estimated)**2 / factor
            velocity_residual = (v[i] - velocity_estimated)**2 / factor

            sum_depth_residual += depth_residual
            sum_velocity_residual += velocity_residual

            row.update({
                "omega": omega,
                "depth_estimated_m": depth_estimated,
                "velocity_estimated_m_s": velocity_estimated,
                "depth_residual": depth_residual,
                "velocity_residual": velocity_residual,
            })

        rows.append(row)

    sd_depth_ive = sqrt(sum_depth_residual / (n - 5))
    sd_velocity_ive = sqrt(sum_velocity_residual / (n - 5))

    sd_depth = max(sd_depth_ive, p.minimum_depth_sd_m)
    # Decision metodologica: utilizar s_v,IVE directamente.
    # No se aplica un minimo instrumental s_v,min.
    sd_velocity = sd_velocity_ive

    variance_width = 0.0
    variance_depth = 0.0
    variance_velocity = 0.0

    for i, row in enumerate(rows):
        vb = (q_values[i] * p.width_relative_per_vertical)**2
        vd = (widths[i] * v[i] * sd_depth)**2

        # Only a boundary explicitly preserving source velocity contributes
        # velocity variance; synthetic banks always have zero velocity.
        boundary_preserves_velocity = (
            (i == 0 and p.left_bank_mode == "preserve_both")
            or (i == len(nodes) - 1 and p.right_bank_mode == "preserve_both")
        )
        vv = (
            (widths[i] * d[i] * sd_velocity)**2
            if 0 < i < len(nodes) - 1 or boundary_preserves_velocity
            else 0.0
        )

        variance_width += vb
        variance_depth += vd
        variance_velocity += vv

        row.update({
            "variance_width": vb,
            "variance_depth": vd,
            "variance_velocity": vv,
        })

    if q_mid == 0:
        return IVECalculation(
            status="not_available",
            vertical_count=n,
            q_mid_m3s=q_mid,
            relative_uncertainty_pct=None,
            absolute_uncertainty_m3s=None,
            quality="IVE no disponible: caudal nulo",
            sd_depth_ive_m=sd_depth_ive,
            sd_velocity_ive_m_s=sd_velocity_ive,
            sd_depth_used_m=sd_depth,
            sd_velocity_used_m_s=sd_velocity,
            uncertainty_width_relative=None,
            uncertainty_depth_relative=None,
            uncertainty_velocity_relative=None,
            details=tuple(rows),
        )

    uq = sqrt(
        (q_mid * p.systematic_relative)**2
        + variance_width
        + variance_depth
        + variance_velocity
    )

    ur = uq / abs(q_mid)

    return IVECalculation(
        status="calculated",
        vertical_count=n,
        q_mid_m3s=q_mid,
        relative_uncertainty_pct=100 * ur,
        absolute_uncertainty_m3s=uq,
        quality=classify_ive(100 * ur),
        sd_depth_ive_m=sd_depth_ive,
        sd_velocity_ive_m_s=sd_velocity_ive,
        sd_depth_used_m=sd_depth,
        sd_velocity_used_m_s=sd_velocity,
        uncertainty_width_relative=sqrt(variance_width) / abs(q_mid),
        uncertainty_depth_relative=sqrt(variance_depth) / abs(q_mid),
        uncertainty_velocity_relative=sqrt(variance_velocity) / abs(q_mid),
        details=tuple(rows),
    )
