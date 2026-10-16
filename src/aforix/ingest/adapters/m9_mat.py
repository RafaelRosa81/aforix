"""Reader for Matlab exports produced by SonTek RiverSurveyor Live."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
from scipy.io import loadmat

from aforix.analysis.quality.ive import calculate_ive_profile


MATLAB_EPOCH = datetime(2000, 1, 1)


def _field(struct: Any, name: str, default: Any = None) -> Any:
    return getattr(struct, name, default) if struct is not None else default


def _scalar(value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    arr = np.asarray(value)
    if arr.size == 0:
        return default
    item = arr.reshape(-1)[0]
    if isinstance(item, bytes):
        return item.decode("utf-8", errors="replace").strip()
    if isinstance(item, np.generic):
        item = item.item()
    if isinstance(item, float) and not np.isfinite(item):
        return default
    return item


def _array(struct: Any, name: str, *, ndim: int = 1) -> np.ndarray:
    value = _field(struct, name)
    if value is None:
        return np.empty((0,) if ndim == 1 else (0, ndim), dtype=float)
    arr = np.asarray(value, dtype=float)
    return arr


def _valid_mean(values: np.ndarray) -> float | None:
    values = np.asarray(values, dtype=float).reshape(-1)
    valid = values[np.isfinite(values) & (values > 0)]
    return float(valid.mean()) if valid.size else None


def _timestamp(seconds: float, timezone_name: str) -> datetime:
    # RSL writes System.Time as epoch seconds but aligned to the acquisition
    # computer's wall clock. Treating it as UTC shifts these Uruguay transects
    # by three hours and disagrees with the timestamp in the exported filename.
    local_dt = MATLAB_EPOCH + timedelta(seconds=float(seconds))
    return local_dt.replace(tzinfo=ZoneInfo(timezone_name))


def _projected_track(track: np.ndarray) -> tuple[np.ndarray, float | None]:
    if track.ndim != 2 or track.shape[1] < 2 or len(track) < 2:
        return np.full(len(track), np.nan), None
    valid = np.isfinite(track[:, :2]).all(axis=1)
    if valid.sum() < 2:
        return np.full(len(track), np.nan), None
    pts = track[valid, :2]
    delta = pts[-1] - pts[0]
    span = float(np.linalg.norm(delta))
    if span <= 0:
        return np.full(len(track), np.nan), None
    axis = delta / span
    projected = np.full(len(track), np.nan)
    projected[valid] = (pts - pts[0]) @ axis
    return projected, float(np.nanmax(projected) - np.nanmin(projected))


def _distance_from_left_bank(projected: np.ndarray, left_bank_distance_m: float) -> np.ndarray:
    """Shift projected track positions into the full section coordinate system."""
    distance = np.asarray(projected, dtype=float).copy()
    valid = np.isfinite(distance)
    if not valid.any():
        return distance
    # The boat can briefly move behind its first valid track sample. Align the
    # minimum projection with the left edge so every sample uses the same
    # origin and the measured track span matches the Summary width calculation.
    distance[valid] = (
        distance[valid] - float(np.min(distance[valid]))
        + float(left_bank_distance_m or 0.0)
    )
    return distance


def _normal_velocity(
    track: np.ndarray,
    mean_velocity: np.ndarray,
    depth: np.ndarray,
    *,
    coordinate_system: Any,
    reference_discharge: float,
) -> tuple[np.ndarray, str | None]:
    """Project horizontal Mean_Vel onto the cross-section normal."""
    result = np.full(len(track), np.nan, dtype=float)
    coordinate_code = _scalar(coordinate_system)
    if coordinate_code not in (1, 2):  # XYZ or ENU; beam coordinates need another transform.
        return result, None
    if track.ndim != 2 or track.shape[1] < 2 or mean_velocity.ndim != 2 or mean_velocity.shape[1] < 2:
        return result, None
    valid_track = np.isfinite(track[:, :2]).all(axis=1)
    indices = np.flatnonzero(valid_track)
    if len(indices) < 2:
        return result, None
    delta = track[indices[-1], :2] - track[indices[0], :2]
    length = float(np.linalg.norm(delta))
    if length <= 0:
        return result, None
    axis = delta / length
    normal = np.array([-axis[1], axis[0]])
    count = min(len(track), len(mean_velocity), len(depth))
    valid = valid_track[:count] & np.isfinite(mean_velocity[:count, :2]).all(axis=1)
    result[:count][valid] = mean_velocity[:count, :2][valid] @ normal
    valid &= np.isfinite(depth[:count]) & (depth[:count] > 0)
    if valid.sum() >= 2:
        x = (track[:count, :2][valid] - track[indices[0], :2]) @ axis
        order = np.argsort(x, kind="stable")
        q_projection = float(np.trapezoid(depth[:count][valid][order] * result[:count][valid][order], x[order]))
        if np.isfinite(reference_discharge) and q_projection * reference_discharge < 0:
            finite_indices = np.flatnonzero(np.isfinite(result[:count]))
            result[finite_indices] *= -1.0
    label = "ENU" if coordinate_code == 2 else "XYZ"
    return result, f"Mean_Vel_{label}_projected_normal_to_transect"


def _wetted_perimeter(
    distance_m: np.ndarray,
    depth_m: np.ndarray,
    *,
    left_bank_distance_m: float = 0.0,
    right_bank_distance_m: float = 0.0,
) -> float | None:
    """Estimate wetted perimeter from the continuous M9 depth profile.

    The MAT export provides measured depths along the boat track and distances
    from the first/last track sample to each bank. Where a bank offset is
    positive, a straight bed segment is assumed between the bank (zero depth)
    and the nearest measured sample.
    """
    x = np.asarray(distance_m, dtype=float).reshape(-1)
    d = np.asarray(depth_m, dtype=float).reshape(-1)
    valid = np.isfinite(x) & np.isfinite(d) & (d >= 0)
    x, d = x[valid], d[valid]
    if len(x) < 2:
        return None
    order = np.argsort(x)
    x, d = x[order], d[order]
    unique = np.concatenate(([True], np.diff(x) > 1e-9))
    x, d = x[unique], d[unique]
    if len(x) < 2:
        return None

    left = max(0.0, float(left_bank_distance_m or 0.0))
    right = max(0.0, float(right_bank_distance_m or 0.0))
    profile_x = np.concatenate(([x[0] - left], x, [x[-1] + right]))
    profile_d = np.concatenate(([0.0] if left > 0 else [], d, [0.0] if right > 0 else []))
    # If no bank offset was reported, do not invent a dry-margin segment.
    if left <= 0:
        profile_x = profile_x[1:]
    if right <= 0:
        profile_x = profile_x[:-1]
    dx = np.diff(profile_x)
    dd = np.diff(profile_d)
    valid_segments = np.isfinite(dx) & np.isfinite(dd) & (dx > 0)
    if not valid_segments.any():
        return None
    return float(np.sqrt(dx[valid_segments] ** 2 + dd[valid_segments] ** 2).sum())


def parse_m9_mat(path: Path, *, timezone_name: str = "America/Montevideo") -> dict[str, Any]:
    """Parse one RSL .mat transect into a Summary row and sample Points rows.

    The raw .rivr container is not parsed here; RiverSurveyor Live's Matlab
    export is the supported ingest input.
    """
    path = Path(path)
    try:
        data = loadmat(path, squeeze_me=True, struct_as_record=False)
    except (OSError, ValueError, NotImplementedError) as exc:
        raise ValueError(f"Could not read RiverSurveyor Live MAT file {path}: {exc}") from exc
    required = ("SiteInfo", "SystemHW", "System", "Summary")
    missing = [name for name in required if name not in data]
    if missing:
        raise ValueError(f"MAT file lacks required RiverSurveyor structures: {missing}")

    site, hw, system, summary = (data[name] for name in required)
    times = _array(system, "Time")
    if not times.size or not np.isfinite(times).any():
        raise ValueError("MAT file has no usable System.Time samples")
    good_times = times[np.isfinite(times)]
    start_dt = _timestamp(good_times[0], timezone_name)
    end_dt = _timestamp(good_times[-1], timezone_name)

    total_q_values = _array(summary, "Total_Q")
    finite_q = total_q_values[np.isfinite(total_q_values)]
    if not finite_q.size:
        raise ValueError("MAT file has no usable Summary.Total_Q values")
    q_total = float(finite_q[-1])
    area_value = _scalar(_field(summary, "Area"))
    area = float(area_value) if area_value is not None else None
    depths = _array(summary, "Depth")
    depth_mean = _valid_mean(depths)
    depth_max = float(np.nanmax(depths)) if np.isfinite(depths).any() else None

    track = _array(summary, "Track", ndim=2)
    projected, track_span = _projected_track(track)
    setup = data.get("Setup")
    left_edge = _scalar(_field(setup, "Edges_0__DistanceToBank"), 0.0)
    right_edge = _scalar(_field(setup, "Edges_1__DistanceToBank"), 0.0)
    distance_from_left_bank = _distance_from_left_bank(projected, float(left_edge or 0.0))
    edge_total = float(left_edge or 0.0) + float(right_edge or 0.0)
    width = track_span + edge_total if track_span is not None else None
    wetted_perimeter = (
        _wetted_perimeter(
            projected,
            depths,
            left_bank_distance_m=float(left_edge or 0.0),
            right_bank_distance_m=float(right_edge or 0.0),
        )
        if len(depths) == len(projected)
        else None
    )

    mean_v = _array(summary, "Mean_Vel", ndim=2)
    boat_v = _array(summary, "Boat_Vel", ndim=2)
    gps = data.get("GPS")
    compass = data.get("Compass")
    coordinate_system = _field(setup, "coordinateSystem")
    normal_v, normal_velocity_method = _normal_velocity(
        track,
        mean_v,
        depths,
        coordinate_system=coordinate_system,
        reference_discharge=q_total,
    )
    ive = (
        calculate_ive_profile(
            projected,
            depths,
            normal_v,
            left_bank_distance_m=float(left_edge or 0.0),
            right_bank_distance_m=float(right_edge or 0.0),
        )
        if normal_velocity_method
        else {"status": "not_available", "reason": "El MAT no permite derivar la velocidad normal a la sección."}
    )
    n = len(times)

    def sample(name: str, idx: int, *, source: Any = system, default: float = np.nan) -> float:
        arr = _array(source, name)
        return float(arr[idx]) if arr.ndim == 1 and idx < len(arr) else default

    points: list[dict[str, Any]] = []
    previous_q = 0.0
    for idx in range(n):
        elapsed = float(times[idx]) if np.isfinite(times[idx]) else np.nan
        sample_dt = _timestamp(elapsed, timezone_name) if np.isfinite(elapsed) else None
        cumulative_q = float(total_q_values[idx]) if idx < len(total_q_values) and np.isfinite(total_q_values[idx]) else np.nan
        increment_q = cumulative_q - previous_q if np.isfinite(cumulative_q) else np.nan
        if np.isfinite(cumulative_q):
            previous_q = cumulative_q
        point = {
            "sample_number": idx + 1,
            "timestamp": sample_dt.isoformat(timespec="seconds") if sample_dt else None,
            "elapsed_seconds": elapsed - good_times[0] if np.isfinite(elapsed) else np.nan,
            "distance_along_transect_m": float(projected[idx]) if idx < len(projected) else np.nan,
            # Canonical SIH distance is measured from the physical left bank,
            # including the edge distance omitted by the projected boat track.
            "distance_m": float(distance_from_left_bank[idx]) if idx < len(distance_from_left_bank) else np.nan,
            # Aforix's shared Points model fills this with the transect width
            # from Summary during normalization; it is not a sample interval.
            "width_m": np.nan,
            "track_x_m": float(track[idx, 0]) if track.ndim == 2 and idx < len(track) else np.nan,
            "track_y_m": float(track[idx, 1]) if track.ndim == 2 and idx < len(track) else np.nan,
            "depth_m": float(depths[idx]) if idx < len(depths) and np.isfinite(depths[idx]) else np.nan,
            "q_cumulative_m3s": cumulative_q,
            "q_increment_m3s": increment_q,
            "mean_velocity_x_m_s": float(mean_v[idx, 0]) if mean_v.ndim == 2 and idx < len(mean_v) else np.nan,
            "mean_velocity_y_m_s": float(mean_v[idx, 1]) if mean_v.ndim == 2 and idx < len(mean_v) else np.nan,
            "normal_velocity_m_s": float(normal_v[idx]) if idx < len(normal_v) else np.nan,
            # The shared IVE input expects velocity normal to the transect.
            "velocity_mean_m_s": float(normal_v[idx]) if idx < len(normal_v) else np.nan,
            "boat_velocity_x_m_s": float(boat_v[idx, 0]) if boat_v.ndim == 2 and idx < len(boat_v) else np.nan,
            "boat_velocity_y_m_s": float(boat_v[idx, 1]) if boat_v.ndim == 2 and idx < len(boat_v) else np.nan,
            "temperature_c": sample("Temperature", idx),
            "heading_deg": sample("Heading", idx),
            "pitch_deg": sample("Pitch", idx, source=compass),
            "roll_deg": sample("Roll", idx, source=compass),
            "latitude": sample("Latitude", idx, source=gps),
            "longitude": sample("Longitude", idx, source=gps),
        }
        points.append(point)

    return {
        "summary": {
            "station_id": _scalar(_field(site, "Station_Number")),
            "station_name": _scalar(_field(site, "Site_Name")),
            "measurement_start": start_dt,
            "measurement_end": end_dt,
            "q_total_m3s": q_total,
            "area_total_m2": area,
            "wetted_perimeter_m": wetted_perimeter,
            "hydraulic_radius_m": (
                area / wetted_perimeter
                if area is not None and area > 0 and wetted_perimeter and wetted_perimeter > 0
                else None
            ),
            "hydraulic_radius_method": (
                "summary_area_over_profile_wetted_perimeter"
                if area is not None and area > 0 and wetted_perimeter and wetted_perimeter > 0
                else None
            ),
            "width_total_m": width,
            "width_track_span_m": track_span,
            "width_left_bank_distance_m": float(left_edge),
            "width_right_bank_distance_m": float(right_edge),
            "width_method": "projected_track_span_plus_edge_distances" if width is not None else None,
            "velocity_mean_m_s": q_total / area if area and area > 0 else None,
            "velocity_mean_method": "derived_q_over_area" if area and area > 0 else None,
            "depth_mean_m": depth_mean,
            "depth_max_m": depth_max,
            "normal_velocity_method": normal_velocity_method,
            "coordinate_system_code": _scalar(coordinate_system),
            "ive_method": "IVE_ADAPTADO_M9",
            "ive_status": ive.get("status"),
            "ive_reason": ive.get("reason"),
            "ive_profile_sample_count": ive.get("profile_sample_count"),
            "ive_wet_sample_count": ive.get("wet_sample_count"),
            "ive_q_midsection_m3s": ive.get("q_midsection_m3s"),
            "ive_s_d_ive_m": ive.get("s_d_ive_m"),
            "ive_s_d_effective_m": ive.get("s_d_effective_m"),
            "ive_s_v_ive_m_s": ive.get("s_v_ive_m_s"),
            "ive_u_s": ive.get("u_s"),
            "ive_u_b_q": ive.get("u_b_q"),
            "ive_u_d_q": ive.get("u_d_q"),
            "ive_u_v_q": ive.get("u_v_q"),
            "uncertainty_method": "IVE_ADAPTADO_M9",
            "uncertainty_status": ive.get("status"),
            "uncertainty_reason": ive.get("reason"),
            "uncertainty_ive_relative": ive.get("relative_uncertainty"),
            "uncertainty_ive_absolute_m3s": ive.get("absolute_error_m3s"),
            "uncertainty_ive_quality": ive.get("quality"),
            "sample_count": n,
            "serial_number": _scalar(_field(hw, "SerialNumber")),
            "firmware_version": _scalar(_field(hw, "FirmwareVersion")),
            "comments": _scalar(_field(site, "Comments")),
        },
        "points": points,
    }
