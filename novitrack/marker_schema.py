"""Construct and normalize persistent NoviTrack marker records."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def marker_definition(params: Any, marker: str) -> Mapping[str, Any] | None:
    """Return the configured definition for a legacy marker character."""
    table = _get(params, "markers", pd.DataFrame())
    if not isinstance(table, pd.DataFrame) or table.empty or "marker" not in table:
        return None
    marker = str(marker)
    if not marker:
        return None
    matches = table.loc[table["marker"].astype(str) == marker[0]]
    return None if len(matches) != 1 else matches.iloc[0].to_dict()


def normalize_duration(value: Any) -> float:
    """Return a nonnegative duration in seconds, or NaN when unknown."""
    if value is None:
        return float("nan")
    if isinstance(value, np.ndarray) and value.size == 0:
        return float("nan")
    try:
        duration = float(np.asarray(value).reshape(-1)[0])
    except (TypeError, ValueError, IndexError):
        return float("nan")
    return duration if duration >= 0 or np.isnan(duration) else float("nan")


def unknown_opto_parameters() -> dict[str, float]:
    """Return unknown optogenetic settings in the SI units Hz, s, and W."""
    return {
        "frequency": float("nan"),
        "pulse_width": float("nan"),
        "power": float("nan"),
    }


def make_marker_record(
    time: float,
    marker: str,
    params: Any,
    *,
    duration: Any = np.nan,
    parameters: Mapping[str, Any] | None = None,
    marker_id: str | None = None,
) -> dict[str, Any]:
    """Create one marker in the versioned five-field storage format."""
    marker = str(marker)
    definition = marker_definition(params, marker)
    if marker_id is None:
        marker_id = (
            str(definition.get("marker_id", "unknown") or "unknown")
            if definition is not None
            else "unknown"
        )

    marker_parameters = dict(parameters) if isinstance(parameters, Mapping) else {}
    suffix = marker[1:]
    if (
        definition is not None
        and bool(definition.get("linked", False))
        and suffix.isdigit()
        and "stimulus_id" not in marker_parameters
    ):
        marker_parameters["stimulus_id"] = int(suffix)

    return {
        "time": float(time),
        "marker": marker,
        "marker_id": str(marker_id or "unknown"),
        "duration": normalize_duration(duration),
        "parameters": marker_parameters,
    }


def normalize_marker_record(marker: Any, params: Any) -> dict[str, Any]:
    """Normalize a legacy or current marker without discarding extra fields."""
    existing_parameters = _get(marker, "parameters", {})
    marker_id = _get(marker, "marker_id", None)
    if isinstance(marker_id, np.ndarray) and marker_id.size == 0:
        marker_id = None
    normalized = make_marker_record(
        _get(marker, "time", np.nan),
        _get(marker, "marker", ""),
        params,
        duration=_get(marker, "duration", np.nan),
        parameters=existing_parameters if isinstance(existing_parameters, Mapping) else {},
        marker_id=str(marker_id) if marker_id not in (None, "") else None,
    )
    if isinstance(marker, Mapping):
        for name, value in marker.items():
            normalized.setdefault(str(name), value)
    return normalized


def normalize_marker_records(markers: Any, params: Any) -> list[dict[str, Any]]:
    """Normalize a marker collection and sort it chronologically."""
    if markers is None:
        return []
    if isinstance(markers, pd.DataFrame):
        values: Any = markers.to_dict(orient="records")
    elif isinstance(markers, Mapping):
        values = [markers]
    elif isinstance(markers, np.ndarray) and markers.size == 0:
        return []
    else:
        try:
            values = list(markers)
        except TypeError:
            return []
    normalized = [
        normalize_marker_record(marker, params)
        for marker in values
        if isinstance(marker, Mapping) or hasattr(marker, "time")
    ]
    return sorted(normalized, key=lambda marker: marker["time"])


__all__ = [
    "make_marker_record",
    "marker_definition",
    "normalize_duration",
    "normalize_marker_record",
    "normalize_marker_records",
    "unknown_opto_parameters",
]
