"""Compute movement and orientation measures from calibrated pose keypoints."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Any

import numpy as np
from scipy.signal import savgol_coeffs

from .tracking_stream import TrackingStream


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _normalise_name(name: Any) -> str:
    return str(name).strip().casefold().replace("-", "_").replace(" ", "_")


def _true_runs(mask: np.ndarray) -> list[tuple[int, int]]:
    padded = np.concatenate(([False], np.asarray(mask, dtype=bool), [False]))
    changes = np.diff(padded.astype(np.int8))
    return list(zip(np.flatnonzero(changes == 1), np.flatnonzero(changes == -1)))


def _median_sample_interval(times: np.ndarray) -> float:
    differences = np.diff(times)
    differences = differences[np.isfinite(differences) & (differences > 0)]
    return float(np.median(differences)) if differences.size else np.nan


def _interpolate_short_gaps(
    values: np.ndarray,
    times: np.ndarray,
    maximum_gap_seconds: float,
) -> np.ndarray:
    result = np.asarray(values, dtype=float).copy()
    if maximum_gap_seconds <= 0 or result.size == 0:
        return result
    missing = ~np.isfinite(result)
    for start, stop in _true_runs(missing):
        if start == 0 or stop == result.size:
            continue
        if not (np.isfinite(result[start - 1]) and np.isfinite(result[stop])):
            continue
        # The interval occupied by the missing samples is bounded by half a
        # sample interval on either side, which equals this boundary span.
        gap_duration = float(times[stop] - times[start - 1])
        if np.isfinite(gap_duration) and gap_duration <= maximum_gap_seconds + 1e-12:
            result[start:stop] = np.interp(
                times[start:stop],
                [times[start - 1], times[stop]],
                [result[start - 1], result[stop]],
            )
    return result


def _window_samples(window_seconds: float, sample_interval: float, order: int) -> int:
    if window_seconds <= 0 or not np.isfinite(sample_interval) or sample_interval <= 0:
        return 0
    samples = max(order + 1, int(round(window_seconds / sample_interval)))
    if samples % 2 == 0:
        samples += 1
    return samples


def _smooth_finite_runs(values: np.ndarray, window: int, order: int) -> np.ndarray:
    result = np.asarray(values, dtype=float).copy()
    if window <= 1:
        return result
    coefficients = savgol_coeffs(window, order)
    half_window = window // 2
    for start, stop in _true_runs(np.isfinite(result)):
        length = stop - start
        if length < window:
            continue
        padded = np.pad(
            result[start:stop],
            (half_window, half_window),
            mode="edge",
        )
        result[start:stop] = np.convolve(padded, coefficients, mode="valid")
    return result


def _configured_keypoint_names(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        values = (value,)
    else:
        try:
            values = tuple(value)
        except TypeError:
            values = ()
    excluded = {"body_center", "tail_center", "tail_tip"}
    result: list[str] = []
    seen: set[str] = set()
    for item in values:
        name = _normalise_name(item)
        if name and name not in excluded and name not in seen:
            result.append(name)
            seen.add(name)
    return tuple(result)


def _reconstruct_body_center(
    position: np.ndarray,
    support_points: list[np.ndarray],
    times: np.ndarray,
    *,
    maximum_gap_seconds: float,
    maximum_speed: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Fill eligible body-centre gaps by following stable support keypoints."""
    result = np.asarray(position, dtype=float).copy()
    reconstructed = np.zeros(result.shape[0], dtype=bool)
    if maximum_gap_seconds <= 0 or not support_points:
        return result, reconstructed

    support = np.stack(support_points, axis=1)
    missing = ~np.all(np.isfinite(result), axis=1)
    for start, stop in _true_runs(missing):
        if start == 0 or stop == result.shape[0]:
            continue
        interval = slice(start - 1, stop + 1)
        interval_times = times[interval]
        time_steps = np.diff(interval_times)
        if not (
            np.all(np.isfinite(interval_times))
            and np.all(time_steps > 0)
            and interval_times[-1] - interval_times[0]
            <= maximum_gap_seconds + 1e-12
        ):
            continue

        interval_support = support[interval]
        if not np.all(np.isfinite(interval_support)):
            continue
        if np.isfinite(maximum_speed) and maximum_speed > 0:
            support_speeds = np.linalg.norm(
                np.diff(interval_support, axis=0), axis=2
            ) / time_steps[:, np.newaxis]
            if np.any(support_speeds > maximum_speed):
                continue

        centroid = np.mean(interval_support, axis=1)
        left_offset = result[start - 1] - centroid[0]
        right_offset = result[stop] - centroid[-1]
        fraction = (
            (times[start:stop] - times[start - 1])
            / (times[stop] - times[start - 1])
        )[:, np.newaxis]
        offsets = left_offset + fraction * (right_offset - left_offset)
        candidate = centroid[1:-1] + offsets

        if np.isfinite(maximum_speed) and maximum_speed > 0:
            joined = np.vstack((result[start - 1], candidate, result[stop]))
            joined_speeds = (
                np.linalg.norm(np.diff(joined, axis=0), axis=1) / time_steps
            )
            if np.any(joined_speeds > maximum_speed):
                continue

        result[start:stop] = candidate
        reconstructed[start:stop] = True
    return result, reconstructed


def _filtered_keypoint(
    keypoints: np.ndarray,
    likelihood: np.ndarray,
    index: int,
    times: np.ndarray,
    *,
    likelihood_cutoff: float,
    maximum_gap_seconds: float,
    smoothing_window: int,
    smoothing_order: int,
) -> np.ndarray:
    point = np.asarray(keypoints[:, index, :], dtype=float).copy()
    valid = np.all(np.isfinite(point), axis=1)
    if likelihood.ndim == 2 and likelihood.shape[:2] == keypoints.shape[:2]:
        confidence = likelihood[:, index]
        if np.any(np.isfinite(confidence)):
            valid &= np.isfinite(confidence) & (confidence >= likelihood_cutoff)
    point[~valid] = np.nan
    for coordinate in range(2):
        point[:, coordinate] = _interpolate_short_gaps(
            point[:, coordinate], times, maximum_gap_seconds
        )
        point[:, coordinate] = _smooth_finite_runs(
            point[:, coordinate], smoothing_window, smoothing_order
        )
    return point


def _gradient(values: np.ndarray, times: np.ndarray) -> np.ndarray:
    result = np.full(np.asarray(values).shape, np.nan, dtype=float)
    finite = np.isfinite(values)
    for start, stop in _true_runs(finite):
        # Split again at duplicate/non-increasing timestamps. TrackingStream
        # permits equal timestamps, whereas a derivative does not.
        split_points = np.flatnonzero(np.diff(times[start:stop]) <= 0) + start + 1
        boundaries = np.concatenate(([start], split_points, [stop]))
        for run_start, run_stop in zip(boundaries[:-1], boundaries[1:]):
            if run_stop - run_start < 2:
                continue
            result[run_start:run_stop] = np.gradient(
                values[run_start:run_stop], times[run_start:run_stop]
            )
    return result


def _direction(origin: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    vector = target - origin
    length = np.linalg.norm(vector, axis=1)
    valid = np.all(np.isfinite(vector), axis=1) & (length > 0)
    angle = np.full(length.shape, np.nan)
    angle[valid] = _wrap_degrees(
        np.degrees(np.arctan2(vector[valid, 1], vector[valid, 0]))
    )
    unit = np.full(vector.shape, np.nan)
    unit[valid] = vector[valid] / length[valid, np.newaxis]
    return angle, unit


def _angular_velocity(direction_degrees: np.ndarray, times: np.ndarray) -> np.ndarray:
    result = np.full(direction_degrees.shape, np.nan)
    for start, stop in _true_runs(np.isfinite(direction_degrees)):
        unwrapped = np.unwrap(np.radians(direction_degrees[start:stop]))
        result[start:stop] = np.degrees(_gradient(unwrapped, times[start:stop]))
    return result


def _wrap_degrees(angle: np.ndarray) -> np.ndarray:
    return (np.asarray(angle, dtype=float) + 180.0) % 360.0 - 180.0


def derive_pose_measures(stream: TrackingStream, params: Any) -> TrackingStream:
    """Add calibrated position, speed, and direction measures to a pose stream.

    Directions use the canonical arena convention: right is 0 degrees and
    counter-clockwise is positive. Linear measures use metres and seconds.
    """
    metadata = dict(stream.metadata)
    processing: dict[str, Any] = {"status": "skipped"}
    keypoints = np.asarray(stream.data.get("keypoints_arena", []), dtype=float)
    names = tuple(stream.metadata.get("keypoint_names", ()))
    if keypoints.ndim != 3 or keypoints.shape[-1] != 2:
        processing["reason"] = "calibrated_keypoints_unavailable"
        metadata["derived_measures"] = processing
        return replace(stream, metadata=metadata)
    if keypoints.shape[0] != stream.reference_times.size or keypoints.shape[1] != len(names):
        processing["reason"] = "keypoint_metadata_mismatch"
        metadata["derived_measures"] = processing
        return replace(stream, metadata=metadata)

    times = np.asarray(stream.reference_times, dtype=float)
    sample_interval = _median_sample_interval(times)
    maximum_gap = max(0.0, float(_get(params, "nt_tracking_interpolation_max_gap", 0.1)))
    smoothing_seconds = max(0.0, float(_get(params, "nt_tracking_smoothing_window", 0.2)))
    smoothing_order = max(0, int(_get(params, "nt_tracking_smoothing_polynomial_order", 2)))
    smoothing_window = _window_samples(smoothing_seconds, sample_interval, smoothing_order)
    likelihood_cutoff = float(stream.metadata.get("likelihood_cutoff", 0.6))
    likelihood = np.asarray(stream.data.get("likelihood", []), dtype=float)
    reconstruction_enabled = bool(
        _get(params, "nt_tracking_body_center_reconstruction_enabled", True)
    )
    reconstruction_maximum_gap = max(
        0.0,
        float(_get(params, "nt_tracking_body_center_reconstruction_max_gap", 0.5)),
    )
    reconstruction_maximum_speed = float(
        _get(params, "nt_tracking_body_center_reconstruction_max_speed", 2.0)
    )
    reconstruction_support_names = _configured_keypoint_names(
        _get(
            params,
            "nt_tracking_body_center_reconstruction_support_keypoints",
            ("neck", "tail_base"),
        )
    )

    name_to_index = {_normalise_name(name): index for index, name in enumerate(names)}
    filtered: dict[str, np.ndarray] = {}

    def point(name: str) -> np.ndarray | None:
        normalised = _normalise_name(name)
        index = name_to_index.get(normalised)
        if index is None:
            return None
        if normalised not in filtered:
            filtered[normalised] = _filtered_keypoint(
                keypoints,
                likelihood,
                index,
                times,
                likelihood_cutoff=likelihood_cutoff,
                maximum_gap_seconds=maximum_gap,
                smoothing_window=smoothing_window,
                smoothing_order=smoothing_order,
            )
        return filtered[normalised]

    requested_position = str(_get(params, "nt_tracking_position_keypoint", "body_center"))
    position = point(requested_position)
    position_definition = requested_position
    if position is None:
        for fallback in ("body_center", "com", "center_of_mass", "head_center"):
            position = point(fallback)
            if position is not None:
                position_definition = fallback
                break
    if position is None:
        nose = point("nose")
        tail_base = point("tail_base")
        if nose is not None and tail_base is not None:
            position = (nose + tail_base) / 2.0
            position_definition = "midpoint(nose,tail_base)"
    if position is None:
        processing["reason"] = "position_keypoints_unavailable"
        metadata["derived_measures"] = processing
        return replace(stream, metadata=metadata)

    body_center_reconstructed = np.zeros(times.shape, dtype=bool)
    reconstruction_status = "disabled"
    if reconstruction_enabled and _normalise_name(position_definition) == "body_center":
        support_points = [
            support
            for name in reconstruction_support_names
            if (support := point(name)) is not None
        ]
        if len(support_points) == len(reconstruction_support_names) and support_points:
            position, body_center_reconstructed = _reconstruct_body_center(
                position,
                support_points,
                times,
                maximum_gap_seconds=reconstruction_maximum_gap,
                maximum_speed=reconstruction_maximum_speed,
            )
            reconstruction_status = "computed"
        else:
            reconstruction_status = "support_keypoints_unavailable"
    elif reconstruction_enabled:
        reconstruction_status = "position_is_not_body_center"

    velocity = np.column_stack(
        (_gradient(position[:, 0], times), _gradient(position[:, 1], times))
    )
    speed = np.linalg.norm(velocity, axis=1)
    speed[~np.all(np.isfinite(velocity), axis=1)] = np.nan
    movement_direction = np.full(speed.shape, np.nan)
    moving = np.all(np.isfinite(velocity), axis=1) & (speed > 0)
    movement_direction[moving] = _wrap_degrees(
        np.degrees(np.arctan2(velocity[moving, 1], velocity[moving, 0]))
    )

    body_tail_name = str(_get(params, "nt_tracking_body_direction_tail_keypoint", "tail_base"))
    body_head_name = str(_get(params, "nt_tracking_body_direction_head_keypoint", "neck"))
    body_tail = point(body_tail_name)
    body_head = point(body_head_name)
    if body_tail is None or body_head is None:
        body_tail = point("tail_base")
        body_head = point("head_center")
        if body_head is None:
            body_head = point("nose")
        body_tail_name = "tail_base"
        body_head_name = "head_center" if point("head_center") is not None else "nose"

    body_direction = np.full(speed.shape, np.nan)
    body_unit = np.full(velocity.shape, np.nan)
    if body_tail is not None and body_head is not None:
        body_direction, body_unit = _direction(body_tail, body_head)
    forward_speed = np.sum(velocity * body_unit, axis=1)
    forward_speed[~np.all(np.isfinite(velocity) & np.isfinite(body_unit), axis=1)] = np.nan
    angular_velocity = _angular_velocity(body_direction, times)

    head_origin_name = str(_get(params, "nt_tracking_head_direction_origin_keypoint", "head_center"))
    head_tip_name = str(_get(params, "nt_tracking_head_direction_tip_keypoint", "nose"))
    head_origin = point(head_origin_name)
    head_tip = point(head_tip_name)
    head_direction = np.full(speed.shape, np.nan)
    if head_origin is not None and head_tip is not None:
        head_direction, _head_unit = _direction(head_origin, head_tip)
    head_body_angle = _wrap_degrees(head_direction - body_direction)

    distance_to_center = np.linalg.norm(position, axis=1)
    distance_to_center[~np.all(np.isfinite(position), axis=1)] = np.nan
    data = dict(stream.data)
    data.update(
        {
            "position_arena": position,
            "body_center_reconstructed": body_center_reconstructed,
            "CoM_X": position[:, 0],
            "CoM_Y": position[:, 1],
            "Speed": speed,
            "Forward_speed": forward_speed,
            "body_direction": body_direction,
            "head_direction": head_direction,
            "movement_direction": movement_direction,
            "head_body_angle": head_body_angle,
            "body_angular_velocity": angular_velocity,
            "Angular_velocity": angular_velocity,
            "Abs_angular_velocity": np.abs(angular_velocity),
            "Distance_to_center": distance_to_center,
            "alpha": body_direction,
        }
    )
    processing = {
        "status": "computed",
        "position_definition": position_definition,
        "body_direction_definition": f"{body_tail_name}->{body_head_name}",
        "head_direction_definition": f"{head_origin_name}->{head_tip_name}",
        "likelihood_cutoff": likelihood_cutoff,
        "interpolation_max_gap_seconds": maximum_gap,
        "smoothing_window_seconds": smoothing_seconds,
        "smoothing_window_samples": smoothing_window,
        "smoothing_polynomial_order": smoothing_order,
        "body_center_reconstruction": {
            "status": reconstruction_status,
            "support_keypoints": reconstruction_support_names,
            "maximum_gap_seconds": reconstruction_maximum_gap,
            "maximum_speed_m_per_s": reconstruction_maximum_speed,
            "reconstructed_samples": int(np.count_nonzero(body_center_reconstructed)),
        },
        "angle_convention": "degrees; right=0; counter-clockwise positive; [-180,180)",
        "units": {
            "position_arena": "m",
            "CoM_X": "m",
            "CoM_Y": "m",
            "Speed": "m/s",
            "Forward_speed": "m/s",
            "body_direction": "deg",
            "alpha": "deg",
            "head_direction": "deg",
            "movement_direction": "deg",
            "head_body_angle": "deg",
            "body_angular_velocity": "deg/s",
            "Angular_velocity": "deg/s",
            "Abs_angular_velocity": "deg/s",
            "Distance_to_center": "m",
        },
    }
    metadata["derived_measures"] = processing
    capabilities = set(stream.capabilities) | {"position"}
    for values, capability in (
        (speed, "speed"),
        (forward_speed, "forward_speed"),
        (movement_direction, "movement_direction"),
    ):
        if np.any(np.isfinite(values)):
            capabilities.add(capability)
    if np.any(np.isfinite(body_direction)):
        capabilities |= {"heading", "body_direction", "angular_velocity"}
    if np.any(np.isfinite(head_direction)):
        capabilities |= {"head_direction", "head_body_angle"}
    return replace(stream, data=data, capabilities=capabilities, metadata=metadata)


__all__ = ["derive_pose_measures"]
