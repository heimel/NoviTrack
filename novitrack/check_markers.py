"""Check NoviTrack marker start/stop consistency."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd

from inpythotools.logmsg import logmsg
from .marker_schema import marker_parameters


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _record_label(record: Any) -> str:
    return str(_get(record, "sessionid", _get(record, "subject", "record")))


def check_markers(record: Any, params: Any | None = None, verbose: bool = True) -> bool:
    """Return True when marker starts/stops are self-consistent."""
    if params is None:
        from .load_parameters import load_parameters

        params = load_parameters(record)

    measures = _get(record, "measures", {})
    markers = _get(measures, "markers", None)
    if markers is None or len(markers) == 0:
        return True

    marker_definitions = _get(params, "markers", pd.DataFrame())
    if not isinstance(marker_definitions, pd.DataFrame):
        marker_definitions = pd.DataFrame(marker_definitions)
    configured_stimulus_ids = _get(params, "nt_stim_marker_ids", None)
    if configured_stimulus_ids is None and not marker_definitions.empty:
        linked = marker_definitions[
            marker_definitions["linked"].astype(bool)
            & ~marker_definitions["behavior"].astype(bool)
        ]
        configured_stimulus_ids = linked.loc[
            linked["marker_id"].astype(str) != "stop", "marker_id"
        ].tolist()
    stim_marker_ids = set(str(marker_id) for marker_id in (configured_stimulus_ids or []))
    stop_marker_id = str(_get(params, "nt_stop_marker_id", "stop"))
    active_stimuli: set[Any] = set()
    msg = ""

    for marker in markers:
        marker_id = str(_get(marker, "marker_id", "unknown") or "unknown")
        marker_time = float(_get(marker, "time", np.nan))
        stimulus_id = marker_parameters(marker).get("stimulus_id")
        if marker_id == stop_marker_id:
            if stimulus_id in active_stimuli:
                active_stimuli.remove(stimulus_id)
            elif stimulus_id is None and len(active_stimuli) == 1:
                active_stimuli.clear()
            else:
                msg = f"Stimulus stopped before starting at {marker_time:.2g} s"
                break
        elif marker_id in stim_marker_ids:
            stimulus_key = stimulus_id if stimulus_id is not None else marker_id
            if stimulus_key in active_stimuli:
                msg = f"Stimulus started twice at {marker_time:.2g} s"
                break
            active_stimuli.add(stimulus_key)

    if msg:
        if verbose:
            logmsg(f"{msg} in {_record_label(record)}")
        return False
    return True


__all__ = ["check_markers"]
