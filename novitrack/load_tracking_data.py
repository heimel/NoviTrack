"""Load precomputed NoviTrack tracking data."""

from __future__ import annotations

from collections.abc import Mapping
import os
from pathlib import Path
import tempfile
from typing import Any

import numpy as np
from scipy import signal
from scipy.io import loadmat, savemat

from inpythotools.mat_database import _convert_mat_value
from inpythotools.logmsg import logmsg
from .load_neurotar_data import load_neurotar_data
from .session_path import session_path as resolve_session_path


TRACKING_SCHEMA_VERSION = 1


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _as_array(value: Any) -> np.ndarray:
    try:
        return np.asarray(value, dtype=float).reshape(-1)
    except (TypeError, ValueError):
        if isinstance(value, (list, tuple)):
            parts = [_as_array(item) for item in value]
            parts = [part for part in parts if part.size]
            if parts:
                return np.concatenate(parts)
        return np.array([], dtype=float)


def _median_filter_omitnan(x: np.ndarray, width: int) -> np.ndarray:
    """Median filter roughly matching MATLAB ``medfilt1(...,'omitnan')``."""
    x = _as_array(x)
    if width <= 1 or x.size == 0:
        return x

    if width % 2 == 0:
        width += 1
    return signal.medfilt(x, kernel_size=width)


def _ensure_field(nt_data: dict[str, Any], field: str, value: Any) -> None:
    if field not in nt_data or np.asarray(nt_data[field]).size == 0:
        nt_data[field] = value


def _complete_tracking_fields(nt_data: dict[str, Any], params: Any) -> dict[str, Any]:
    """Add derived/default fields expected by downstream NoviTrack analysis."""
    time = _as_array(nt_data.get("Time", []))
    if time.size == 0:
        return nt_data

    n = time.size
    nan_vec = np.full(n, np.nan)
    filter_width = int(_get(params, "nt_pose_temporal_filter_width", 20))

    for x_name, y_name in (("X", "Y"), ("CoM_X", "CoM_Y"), ("tailbase_X", "tailbase_Y")):
        if x_name in nt_data:
            nt_data[x_name] = _median_filter_omitnan(_as_array(nt_data[x_name]), filter_width)
            nt_data[y_name] = _median_filter_omitnan(_as_array(nt_data[y_name]), filter_width)

    if "Speed" not in nt_data:
        if "CoM_X" in nt_data:
            dt = float(np.nanmean(np.diff(time)))
            overhead_mm_per_pixel = 0.5
            speed = np.full(n, np.nan)
            speed[:-1] = (
                np.sqrt(np.diff(_as_array(nt_data["CoM_X"])) ** 2 + np.diff(_as_array(nt_data["CoM_Y"])) ** 2)
                / dt
                * overhead_mm_per_pixel
                / 1000
            )
            nt_data["Speed"] = speed
        else:
            nt_data["Speed"] = nan_vec.copy()

    _ensure_field(nt_data, "X", nan_vec.copy())
    _ensure_field(nt_data, "Y", nan_vec.copy())
    _ensure_field(nt_data, "Coordinates", _get(params, "OVERHEAD", 4))
    _ensure_field(nt_data, "CoM_X", nan_vec.copy())
    _ensure_field(nt_data, "CoM_Y", nan_vec.copy())
    _ensure_field(nt_data, "tailbase_X", nan_vec.copy())
    _ensure_field(nt_data, "tailbase_Y", nan_vec.copy())

    if "alpha" not in nt_data:
        alpha = nan_vec.copy()
        if np.any(~np.isnan(nt_data["X"])) and np.any(~np.isnan(nt_data["CoM_X"])):
            vx = _as_array(nt_data["X"]) - _as_array(nt_data["CoM_X"])
            vy = _as_array(nt_data["Y"]) - _as_array(nt_data["CoM_Y"])
            alpha = np.angle(vy + 1j * vx) / np.pi * 180
        nt_data["alpha"] = alpha

    _ensure_field(nt_data, "Forward_speed", nan_vec.copy())

    if "Angular_velocity" not in nt_data:
        angular_velocity = nan_vec.copy()
        alpha = _as_array(nt_data["alpha"])
        if np.any(~np.isnan(alpha)):
            dt = float(np.nanmean(np.diff(time)))
            angular_velocity[1:] = np.angle(np.exp(1j * np.diff(alpha) / 180 * np.pi)) / dt
            angular_velocity = _median_filter_omitnan(angular_velocity, filter_width)
        nt_data["Angular_velocity"] = angular_velocity

    if "Abs_angular_velocity" not in nt_data:
        nt_data["Abs_angular_velocity"] = np.abs(_as_array(nt_data["Angular_velocity"]))

    if "Distance_to_center" not in nt_data:
        nt_data["Distance_to_center"] = np.sqrt(_as_array(nt_data["CoM_X"]) ** 2 + _as_array(nt_data["CoM_Y"]) ** 2)

    _ensure_field(nt_data, "Object_distance", nan_vec.copy())
    return nt_data


def _save_tracking_data(filename: Path, nt_data: dict[str, Any]) -> None:
    """Atomically save a MATLAB-compatible NoviTrack tracking cache."""
    filename.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{filename.stem}.", suffix=".mat", dir=filename.parent, delete=False
        ) as temporary:
            temporary_name = temporary.name
        savemat(
            temporary_name,
            {"nt_data": nt_data},
            appendmat=False,
            do_compression=True,
            long_field_names=True,
            oned_as="column",
        )
        os.replace(temporary_name, filename)
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def _overhead_video(video_info: Any, params: Any) -> Any:
    try:
        videos = list(video_info or [])
    except TypeError:
        videos = [video_info]
    if not videos:
        return None

    # nt_overhead_camera follows MATLAB's one-based indexing in the shared params.
    overhead_index = int(_get(params, "nt_overhead_camera", 1)) - 1
    info = videos[overhead_index] if 0 <= overhead_index < len(videos) else None
    if info is None:
        info = next((candidate for candidate in videos if candidate is not None), None)
    return info


def _normalized_video_triggers(video_info: Any, params: Any) -> np.ndarray:
    info = _overhead_video(video_info, params)
    if info is None:
        return np.array([], dtype=float)
    video_triggers = _as_array(_get(info, "trigger_times", []))
    if video_triggers.size == 0:
        return video_triggers
    return video_triggers - video_triggers[0]


def _video_timeline(video_info: Any, params: Any) -> tuple[dict[str, Any], np.ndarray]:
    """Construct an empty tracking dataset on the overhead-video timeline."""
    info = _overhead_video(video_info, params)
    if info is None:
        return {}, np.array([], dtype=float)

    n_frames = int(_get(info, "n_frames", 0))
    framerate = float(_get(info, "framerate", 0.0))
    if n_frames <= 0 or not np.isfinite(framerate) or framerate <= 0:
        return {}, np.array([], dtype=float)

    video_triggers = _as_array(_get(info, "trigger_times", []))
    first_trigger = float(video_triggers[0]) if video_triggers.size else 0.0
    nt_data = {
        "schema_version": TRACKING_SCHEMA_VERSION,
        "Time": np.arange(n_frames, dtype=float) / framerate - first_trigger,
    }
    trigger_times = _normalized_video_triggers(video_info, params)
    return _complete_tracking_fields(nt_data, params), trigger_times


def load_tracking_data(
    record: Any,
    params: Any,
    *,
    recompute: bool | None = None,
    session_path: str | Path | None = None,
    video_info: Any = None,
    save_cache: bool = True,
) -> tuple[dict[str, Any], np.ndarray]:
    """Load or construct tracking data in the shared NoviTrack MAT format."""
    if recompute is None:
        recompute = bool(_get(params, "nt_recompute_tracking_data", False))

    if session_path is None:
        folder, exists = resolve_session_path(record, params)
    else:
        folder = Path(session_path)
        exists = folder.is_dir()

    if not exists:
        logmsg(f"Folder {folder} does not exist.")
        return {}, _as_array(_get(_get(record, "measures", {}), "trigger_times", []))

    filename = folder / "nt_tracking_data.mat"
    if filename.exists() and not recompute:
        mat = loadmat(filename, squeeze_me=True, struct_as_record=False)
        nt_data = _convert_mat_value(mat["nt_data"])
        nt_data = _complete_tracking_fields(nt_data, params)
        trigger_times = _as_array(_get(_get(record, "measures", {}), "trigger_times", []))
        if trigger_times.size == 0:
            trigger_times = _normalized_video_triggers(video_info, params)
        return nt_data, trigger_times

    nt_data, _ = load_neurotar_data(record, params)
    if nt_data:
        logmsg("Not yet reading in all triggers. Assuming one trigger broadcast by Neurotar at time 0.")
        nt_data.setdefault("schema_version", TRACKING_SCHEMA_VERSION)
        nt_data = _complete_tracking_fields(nt_data, params)
        if save_cache:
            _save_tracking_data(filename, nt_data)
        return nt_data, np.array([0.0])

    nt_data, trigger_times = _video_timeline(video_info, params)
    if nt_data:
        if save_cache:
            _save_tracking_data(filename, nt_data)
            logmsg(f"Saved tracking data to {filename}")
        return nt_data, trigger_times

    if recompute:
        logmsg("Non-Neurotar pose-tracking import branches are not ported yet. Loading precomputed data if present.")

    if filename.exists():
        mat = loadmat(filename, squeeze_me=True, struct_as_record=False)
        nt_data = _convert_mat_value(mat["nt_data"])
        nt_data = _complete_tracking_fields(nt_data, params)
        trigger_times = _as_array(_get(_get(record, "measures", {}), "trigger_times", []))
        return nt_data, trigger_times

    logmsg(f"Precomputed tracking data not found: {filename}")
    return {}, _as_array(_get(_get(record, "measures", {}), "trigger_times", []))
