"""Compute per-event NoviTrack measures."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

import numpy as np
import pandas as pd

from inpythotools.ivt_sem import ivt_sem
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


def _marker_list(params: Any) -> list[dict[str, Any]]:
    markers = _get(params, "markers", [])
    if isinstance(markers, pd.DataFrame):
        return markers.to_dict(orient="records")
    if isinstance(markers, list):
        return markers
    return list(markers)


def _behavior_motifs(params: Any) -> list[str]:
    motifs: list[str] = []
    for marker in _marker_list(params):
        if bool(_get(marker, "behavior", False)):
            motifs.append(str(_get(marker, "marker_id")))
    return motifs


def _get_behaviors(events: pd.DataFrame, motif_list: list[str]) -> pd.DataFrame:
    keep = events["marker_id"].astype(str).isin(set(motif_list))
    return events.loc[keep].reset_index(drop=True)


def _safe_mean(values: Any) -> float:
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return np.nan
    return float(np.nanmean(arr))


def _safe_div(num: float, den: float) -> float:
    return float(num / den) if den != 0 else np.nan


def _parameter(row: Any, name: str, default: Any = None) -> Any:
    parameters = row.get("parameters", {}) if hasattr(row, "get") else _get(row, "parameters", {})
    return parameters.get(name, default) if isinstance(parameters, Mapping) else default


def _same_parameter(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return left is right
    if isinstance(left, np.ndarray) or isinstance(right, np.ndarray):
        left_array = np.asarray(left)
        right_array = np.asarray(right)
        try:
            return bool(np.array_equal(left_array, right_array, equal_nan=True))
        except TypeError:
            return bool(np.array_equal(left_array, right_array))
    try:
        if bool(pd.isna(left)) and bool(pd.isna(right)):
            return True
    except (TypeError, ValueError):
        pass
    try:
        result = left == right
        if isinstance(result, np.ndarray):
            return bool(result.size and np.all(result))
        return bool(result)
    except (TypeError, ValueError):
        return False


def _matching_parameter(rows: pd.DataFrame, name: str, value: Any) -> pd.Series:
    return rows["parameters"].apply(
        lambda parameters: _same_parameter(
            parameters.get(name) if isinstance(parameters, Mapping) else None,
            value,
        )
    )


def _columnar_parameters(records: list[dict[str, Any]]) -> dict[str, np.ndarray]:
    """Convert parameter records to varying arrays or singleton constants."""
    if not records:
        return {}
    table = pd.DataFrame.from_records(records)
    parameters: dict[str, np.ndarray] = {}
    for name in table.columns:
        values = table[name].to_numpy()
        if values.size and all(_same_parameter(values[0], value) for value in values[1:]):
            values = values[:1]
        parameters[str(name)] = values
    return parameters


def compute_event_measures(
    snippets: Mapping[str, Any] | None,
    measures: Mapping[str, Any],
    params: Any,
    *,
    copy: bool = True,
) -> dict[str, Any]:
    """Compute event and behavior measures from snippets and markers."""
    out = deepcopy(dict(measures)) if copy else dict(measures)
    events = get_events(out, params)
    if events.empty:
        out["event"] = {}
        return out

    motif_list = _behavior_motifs(params)
    behaviors = _get_behaviors(events, motif_list)
    unique_events = pd.unique(events["event"])

    out.setdefault("behavior", {})
    motif_set = set(motif_list)
    stop_marker_id = str(_get(params, "nt_stop_marker_id", "stop"))
    posttime = float(_get(params, "nt_posttime", 20))
    has_movie_bounds = "max_time" in out and "min_time" in out
    max_time = float(_get(out, "max_time", np.nan))
    min_time = float(_get(out, "min_time", np.nan))

    for event_type in unique_events:
        event_type = str(event_type)
        if event_type in motif_set:
            continue

        stim_indices = events.index[events["event"] == event_type].to_numpy()
        n_stimuli = len(stim_indices)
        out["behavior"].setdefault(event_type, {})

        for motif in motif_list:
            shortest_latency = np.inf
            total_duration = 0.0
            n_occurrences = 0
            n_responses = 0
            total_stim_duration = 0.0
            intervals: list[float] = []

            for stim_index in stim_indices:
                stim_start = float(events.loc[stim_index, "time"])
                stimulus_id = _parameter(events.loc[stim_index], "stimulus_id")
                duration = float(events.loc[stim_index, "duration"])
                stop_event = "opto_off" if event_type == "opto_on" else stop_marker_id
                stop_candidates = events.index[
                    (events["time"] > stim_start)
                    & (events["marker_id"] == stop_event)
                    & _matching_parameter(events, "stimulus_id", stimulus_id)
                ].to_numpy()
                if np.isfinite(duration) and duration > 0:
                    stim_stop = stim_start + duration
                elif stop_candidates.size == 0:
                    if event_type == "opto_off":
                        stim_stop = stim_start + posttime
                        if np.isfinite(max_time):
                            stim_stop = min(stim_stop, max_time)
                    else:
                        logmsg(f"Stop marker missing for event type {event_type}. Temporarily taking to end of video.")
                        stim_stop = max_time
                else:
                    stim_stop = float(events.loc[stop_candidates[0], "time"])

                stim_duration = stim_stop - stim_start
                total_stim_duration += stim_duration

                behavior_indices = behaviors.index[
                    (behaviors["time"] > stim_start)
                    & (behaviors["time"] < stim_stop)
                    & (behaviors["event"] == motif)
                ].to_numpy()
                if stimulus_id is not None and behavior_indices.size:
                    candidate_behaviors = behaviors.loc[behavior_indices]
                    linked = candidate_behaviors["parameters"].apply(
                        lambda values: isinstance(values, Mapping) and "stimulus_id" in values
                    )
                    matches = _matching_parameter(candidate_behaviors, "stimulus_id", stimulus_id)
                    behavior_indices = candidate_behaviors.index[~linked | matches].to_numpy()
                if behavior_indices.size == 0:
                    continue

                n_responses += 1
                n_occurrences += int(behavior_indices.size)
                latency = float(behaviors.loc[behavior_indices[0], "time"] - stim_start)
                shortest_latency = min(shortest_latency, latency)
                intervals.extend(np.diff(behaviors.loc[behavior_indices, "time"].to_numpy()).tolist())

                for behavior_index in behavior_indices:
                    if behavior_index == len(behaviors) - 1:
                        duration = stim_stop - float(behaviors.loc[behavior_index, "time"])
                        logmsg(f"No end for {behaviors.loc[behavior_index, 'event']}. Taking end of stimulus")
                    else:
                        duration = float(
                            behaviors.loc[behavior_index + 1, "time"]
                            - behaviors.loc[behavior_index, "time"]
                        )
                    total_duration += duration

            out["behavior"][event_type][motif] = {
                "n_occurrences_per_stimulus": _safe_div(n_occurrences, n_stimuli),
                "n_responses_per_stimulus": _safe_div(n_responses, n_stimuli),
                "shortest_latency": shortest_latency,
                "duration_per_stimulus": _safe_div(total_duration, n_stimuli),
                "duration_fraction": _safe_div(total_duration, total_stim_duration),
                "duration_per_occurrence": _safe_div(total_duration, n_occurrences),
                "interval": _safe_mean(intervals),
                "rate": _safe_div(n_occurrences, total_stim_duration),
            }

    out["behavior"].setdefault("session", {})
    for motif in motif_list:
        behavior_indices = behaviors.index[behaviors["event"] == motif].to_numpy()
        n_occurrences = int(behavior_indices.size)
        total_duration = 0.0
        for behavior_index in behavior_indices:
            if behavior_index == len(behaviors) - 1:
                duration = max_time - float(behaviors.loc[behavior_index, "time"])
                logmsg(f"No end for {behaviors.loc[behavior_index, 'event']}")
            else:
                duration = float(
                    behaviors.loc[behavior_index + 1, "time"] - behaviors.loc[behavior_index, "time"]
                )
            total_duration += duration

        marked_period = float(events["time"].iloc[-1] - events["time"].iloc[0])
        if has_movie_bounds:
            movie_duration = max_time - min_time
        else:
            logmsg("Unknown movie duration. Run track_behavior to retrieve this.")
            movie_duration = np.nan
        # MATLAB code uses events.time(ind) here, even though ind indexes behaviors.
        event_times_at_behavior_indices = events.loc[behavior_indices, "time"].to_numpy() if n_occurrences else []

        out["behavior"]["session"][motif] = {
            "n_occurrences_per_session": n_occurrences,
            "duration_per_session": total_duration,
            "duration_per_occurrence": _safe_div(total_duration, n_occurrences),
            "interval": _safe_mean(np.diff(event_times_at_behavior_indices)),
            "duration_fraction": _safe_div(total_duration, marked_period),
            "rate": _safe_div(n_occurrences, marked_period),
            "duration_fraction_of_movie": _safe_div(total_duration, movie_duration),
            "rate_in_movie": _safe_div(n_occurrences, movie_duration),
        }

    if not snippets:
        out["event"] = {}
        return out

    data = _get(snippets, "data", {})
    units = _get(snippets, "unit", {})
    if not data:
        out["event"] = {}
        return out

    mask_post = _as_array(_get(out, "snippets_tbins")) > 0
    out["event"] = {}

    for event_type in unique_events:
        event_type = str(event_type)
        event_indices = events.index[events["event"] == event_type].to_numpy()
        event_parameter_records = [dict(value) for value in events.loc[event_indices, "parameters"]]
        event_durations = events.loc[event_indices, "duration"].to_numpy(dtype=float)
        out["event"][event_type] = {
            "parameters": _columnar_parameters(event_parameter_records),
            "duration": event_durations,
        }
        for field, values in data.items():
            arr = np.asarray(values, dtype=float)
            event_data = arr[event_indices, :]
            snippet_mean = np.nanmean(event_data, axis=0)
            snippet_sem = (
                ivt_sem(event_data, axis=0)
                if len(event_indices) > 1
                else np.full_like(snippet_mean, np.nan)
            )
            out["event"][event_type][field] = {
                "snippet_mean": snippet_mean,
                "snippet_first": event_data[0, :],
                "snippet_std": np.nanstd(event_data, axis=0, ddof=0),
                "snippet_sem": snippet_sem,
                "mean": float(np.nanmean(snippet_mean[mask_post])),
                "max": float(np.nanmax(snippet_mean[mask_post])),
                "min": float(np.nanmin(snippet_mean[mask_post])),
                "n": int(len(event_indices)),
                "event_mean": np.nanmean(event_data, axis=1),
                "unit": _get(units, field, None),
            }

    return out
