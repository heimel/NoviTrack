"""Version and migrate the persistent ``record["measures"]`` structure.

The migration functions in this module are deliberately additive.  In
particular, legacy marker fields remain available so older MATLAB analysis
code can continue to read databases written by Python NoviTrack.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .load_parameters import load_parameters


# Date-coded schema version.  Increment this when the persisted measures
# structure changes and add a corresponding migration step below.
CURRENT_MEASURES_VERSION = 20260831


@dataclass(frozen=True)
class MeasuresMigrationReport:
    """Summary of changes made while upgrading a database in memory."""

    records_upgraded: int = 0
    markers_upgraded: int = 0
    unknown_markers: tuple[tuple[str, float, str], ...] = ()

    @property
    def changed(self) -> bool:
        return self.records_upgraded > 0


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, np.ndarray):
        return value.size == 0
    if isinstance(value, (str, bytes, Mapping, list, tuple)):
        return len(value) == 0
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _measures_version(measures: Mapping[str, Any]) -> int:
    value = measures.get("measures_version", 0)
    if _is_empty(value):
        return 0
    try:
        return int(np.asarray(value).reshape(-1)[0])
    except (TypeError, ValueError, IndexError):
        return 0


def _text(value: Any, default: str = "") -> str:
    if _is_empty(value):
        return default
    if isinstance(value, np.ndarray) and value.size == 1:
        value = value.item()
    return str(value)


def _marker_records(value: Any) -> list[Mapping[str, Any]]:
    """Return markers as records, including singleton MATLAB structs."""
    if value is None:
        return []
    if isinstance(value, pd.DataFrame):
        return value.to_dict(orient="records")
    if isinstance(value, Mapping):
        return [value]
    if isinstance(value, np.ndarray) and value.size == 0:
        return []
    try:
        records = list(value)
    except TypeError:
        return []
    return [record for record in records if isinstance(record, Mapping)]


def _marker_definition_map(record: Any) -> dict[str, Mapping[str, Any] | None]:
    """Map legacy character codes to unique definitions for one marker set."""
    params = load_parameters(record, apply_local_overrides=False)
    definitions: dict[str, list[Mapping[str, Any]]] = {}
    for row in params.markers.to_dict(orient="records"):
        code = str(row.get("marker", ""))
        if code:
            definitions.setdefault(code, []).append(row)
    return {
        code: rows[0] if len(rows) == 1 else None
        for code, rows in definitions.items()
    }


def _duration(value: Any) -> float:
    if _is_empty(value):
        return float("nan")
    try:
        duration = float(np.asarray(value).reshape(-1)[0])
    except (TypeError, ValueError, IndexError):
        return float("nan")
    return duration if duration >= 0 or np.isnan(duration) else float("nan")


def _convert_marker(
    marker: Mapping[str, Any],
    definitions: Mapping[str, Mapping[str, Any] | None],
) -> tuple[dict[str, Any], bool]:
    """Convert one legacy marker without inferring duration or other events."""
    legacy_marker = _text(_get(marker, "marker", ""))
    definition = definitions.get(legacy_marker[:1]) if legacy_marker else None

    existing_marker_id = _text(_get(marker, "marker_id", ""))
    if existing_marker_id:
        marker_id = existing_marker_id
    elif definition is not None:
        marker_id = str(definition.get("marker_id", "unknown") or "unknown")
    else:
        marker_id = "unknown"

    existing_parameters = _get(marker, "parameters", {})
    parameters = dict(existing_parameters) if isinstance(existing_parameters, Mapping) else {}
    suffix = legacy_marker[1:]
    if (
        definition is not None
        and bool(definition.get("linked", False))
        and suffix.isdigit()
        and "stimulus_id" not in parameters
    ):
        parameters["stimulus_id"] = int(suffix)

    converted = {
        "time": float(_get(marker, "time", np.nan)),
        "marker": legacy_marker,
        "marker_id": marker_id,
        "duration": _duration(_get(marker, "duration", np.nan)),
        "parameters": parameters,
    }
    # Preserve any future or locally added fields during an idempotent upgrade.
    for name, value in marker.items():
        converted.setdefault(str(name), value)
    return converted, marker_id == "unknown"


def _record_cache_key(record: Any) -> tuple[str, str, str]:
    """Fields that determine the selected NoviTrack marker set."""
    return tuple(
        _text(_get(record, name, "")).lower()
        for name in ("setup", "condition", "stimulus")
    )


def upgrade_database_measures(
    db: pd.DataFrame,
) -> tuple[pd.DataFrame, MeasuresMigrationReport]:
    """Upgrade outdated measures records to the current in-memory schema.

    Current-version records take the fast path: only ``measures_version`` is
    read. Marker definitions are loaded, cached, and applied only for records
    that actually require migration.
    """
    if not isinstance(db, pd.DataFrame):
        raise TypeError("upgrade_database_measures expects a pandas DataFrame.")
    if "measures" not in db.columns or db.empty:
        return db, MeasuresMigrationReport()

    outdated: list[Any] = []
    for index, measures in db["measures"].items():
        if not isinstance(measures, Mapping) or not measures:
            continue
        if _measures_version(measures) < CURRENT_MEASURES_VERSION:
            outdated.append(index)

    if not outdated:
        return db, MeasuresMigrationReport()

    upgraded = db.copy()
    definition_cache: dict[tuple[str, str, str], dict[str, Mapping[str, Any] | None]] = {}
    markers_upgraded = 0
    unknown: list[tuple[str, float, str]] = []

    for index in outdated:
        record = upgraded.loc[index]
        measures = dict(record["measures"])
        converted_markers: list[dict[str, Any]] = []
        if "markers" in measures:
            marker_records = _marker_records(measures.get("markers", []))
            if marker_records:
                cache_key = _record_cache_key(record)
                definitions = definition_cache.get(cache_key)
                if definitions is None:
                    definitions = _marker_definition_map(record)
                    definition_cache[cache_key] = definitions

                session_id = _text(_get(record, "sessionid", index), str(index))
                for marker in marker_records:
                    converted, is_unknown = _convert_marker(marker, definitions)
                    converted_markers.append(converted)
                    markers_upgraded += 1
                    if is_unknown:
                        unknown.append(
                            (session_id, float(converted["time"]), str(converted["marker"]))
                        )
            measures["markers"] = converted_markers
        measures["measures_version"] = CURRENT_MEASURES_VERSION
        upgraded.at[index, "measures"] = measures

    return upgraded, MeasuresMigrationReport(
        records_upgraded=len(outdated),
        markers_upgraded=markers_upgraded,
        unknown_markers=tuple(unknown),
    )


__all__ = [
    "CURRENT_MEASURES_VERSION",
    "MeasuresMigrationReport",
    "upgrade_database_measures",
]
