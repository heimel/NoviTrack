"""Create NoviTrack event tables from marker annotations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd

from .marker_schema import marker_parameters


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def get_events(measures: Any, params: Any | None = None) -> pd.DataFrame:
    """Create an events DataFrame from ``measures["markers"]``.

    This mirrors ``get_events.m``. Events are derived on demand so saved
    databases do not need to store MATLAB table objects. ``event`` is retained
    as the analysis-facing name for ``marker_id``. Event-specific values remain
    available in ``parameters`` and are also expanded into columns, which makes
    filtering trials by values such as ``frequency`` straightforward.
    """
    markers = _get(measures, "markers", None)
    if markers is None or len(markers) == 0:
        return pd.DataFrame(
            {
                "time": pd.Series(dtype=float),
                "event": pd.Series(dtype=str),
                "marker_id": pd.Series(dtype=str),
                "duration": pd.Series(dtype=float),
                "parameters": pd.Series(dtype=object),
            }
        )

    parameter_records = [marker_parameters(marker) for marker in markers]
    events = pd.DataFrame(
        {
            "time": [float(_get(marker, "time")) for marker in markers],
            "event": [str(_get(marker, "marker_id", "unknown") or "unknown") for marker in markers],
            "duration": [float(_get(marker, "duration", np.nan)) for marker in markers],
            "parameters": parameter_records,
        }
    )
    events.insert(2, "marker_id", events["event"])

    reserved = set(events.columns)
    parameter_names = sorted({str(name) for values in parameter_records for name in values} - reserved)
    for name in parameter_names:
        events[name] = [values.get(name, np.nan) for values in parameter_records]

    pretime = float(_get(params, "nt_pretime", 10))

    if bool(_get(params, "use_clean_baseline", False)):
        index = 0
        while index < len(events):
            row = events.iloc[index]
            remove = (
                (events["time"] > row["time"])
                & (events["time"] < row["time"] + pretime)
                & (events["event"] == row["event"])
            )
            events = events.loc[~remove].reset_index(drop=True)
            index += 1

    if bool(_get(params, "use_ultraclean_baseline", False)):
        index = 0
        while index < len(events):
            row = events.iloc[index]
            remove = (events["time"] > row["time"]) & (events["time"] < row["time"] + pretime)
            events = events.loc[~remove].reset_index(drop=True)
            index += 1

    return events
