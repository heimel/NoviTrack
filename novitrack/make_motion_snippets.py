"""Cut peri-event snippets from NoviTrack motion traces."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

import numpy as np

from inpythotools.logmsg import logmsg
from .get_events import get_events


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _as_array(value: Any) -> np.ndarray:
    return np.asarray(value, dtype=float).reshape(-1)


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, Mapping):
        return len(value) == 0
    try:
        return len(value) == 0
    except TypeError:
        return False


_DEFAULT_MOTION_OBSERVABLES = (
    "Speed",
    "Forward_speed",
    "Abs_angular_velocity",
    "Distance_to_center",
)

_KNOWN_UNITS = {
    "Speed": "m/s",
    "Forward_speed": "m/s",
    "Angular_velocity": "deg/s",
    "Abs_angular_velocity": "deg/s",
    "body_angular_velocity": "deg/s",
    "body_direction": "deg",
    "head_direction": "deg",
    "movement_direction": "deg",
    "head_body_angle": "deg",
}


def _motion_observables(params: Any) -> tuple[str, ...]:
    configured = _get(
        params,
        "nt_motion_snippet_observables",
        _DEFAULT_MOTION_OBSERVABLES,
    )
    if isinstance(configured, str):
        configured = [configured]
    try:
        names = [str(name) for name in configured]
    except TypeError:
        names = list(_DEFAULT_MOTION_OBSERVABLES)
    return tuple(dict.fromkeys(name for name in names if name))


def _interpolate_finite_segments(
    time: np.ndarray,
    values: np.ndarray,
    target_times: np.ndarray,
) -> np.ndarray:
    """Interpolate within finite runs without bridging missing-data gaps."""
    result = np.full(target_times.shape, np.nan, dtype=float)
    finite = np.isfinite(time) & np.isfinite(values)
    padded = np.concatenate(([False], finite, [False]))
    changes = np.diff(padded.astype(np.int8))
    starts = np.flatnonzero(changes == 1)
    stops = np.flatnonzero(changes == -1)
    for start, stop in zip(starts, stops):
        run_time = time[start:stop]
        run_values = values[start:stop]
        if run_time.size < 2:
            continue
        keep = np.concatenate(([True], np.diff(run_time) > 0))
        run_time = run_time[keep]
        run_values = run_values[keep]
        if run_time.size < 2:
            continue
        target_mask = (target_times >= run_time[0]) & (target_times <= run_time[-1])
        result[target_mask] = np.interp(
            target_times[target_mask], run_time, run_values
        )
    return result


def make_motion_snippets(
    nt_data: Any,
    measures: Any,
    snippets: Mapping[str, Any] | None,
    params: Any,
) -> dict[str, Any]:
    """Cut motion snippets around all events.

    This mirrors ``make_motion_snippets.m`` and appends motion observables
    to an existing snippets dictionary when one is supplied.
    """
    if snippets is None or _is_empty(snippets):
        out: dict[str, Any] = {"data": {}, "unit": {}}
    else:
        out = deepcopy(dict(snippets))
        out.setdefault("data", {})
        out.setdefault("unit", {})

    markers = _get(measures, "markers", None)
    if markers is None or len(markers) == 0 or _is_empty(nt_data):
        return out

    events = get_events(measures, params)
    t_bins = _as_array(_get(measures, "snippets_tbins"))
    time = _as_array(_get(nt_data, "Time"))

    pretime = float(_get(params, "nt_pretime", 10))
    posttime = float(_get(params, "nt_posttime", 20))
    bin_width = float(_get(params, "nt_photometry_bin_width", 0.1))

    units = _get(nt_data, "Units", {})
    for observable in _motion_observables(params):
        values = _as_array(_get(nt_data, observable, np.array([])))
        if values.size != time.size or not np.any(np.isfinite(values)):
            continue

        data = np.full((len(events), t_bins.size), np.nan)
        for event_index, event in events.iterrows():
            event_time = float(event["time"])
            mask = (time > event_time - pretime - bin_width) & (
                time < event_time + posttime + bin_width
            )
            if np.any(mask):
                data[event_index, :] = _interpolate_finite_segments(
                    time[mask], values[mask], event_time + t_bins
                )
            else:
                logmsg(f"No samples for event at {event_time}")

        out["data"][observable] = data
        out["unit"][observable] = _get(units, observable, _KNOWN_UNITS.get(observable, "a.u."))

    return out
