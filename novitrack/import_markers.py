"""Import NoviTrack markers from external acquisition and analysis logs.

Persistent marker schema
------------------------
New-format entries in ``record["measures"]["markers"]`` have five fields::

    {
        "time": 40.0,             # onset in master-time seconds
        "marker": "1",           # legacy code retained for MATLAB
        "marker_id": "opto_on",  # descriptive id from params.markers
        "duration": 5.0,          # seconds; NaN when unknown
        "parameters": {
            "frequency": 20.0,    # Hz (SI)
            "pulse_width": 0.01,  # s (SI)
            "power": 0.005,       # W (SI)
        },
    }

``parameters`` contains only values relevant to that marker type; linked
legacy markers such as ``"o2"`` become ``parameters["stimulus_id"] == 2``.
On and off transitions remain separate entries. Databases using the older
``time``/``marker`` representation are upgraded by
``novitrack.measures_schema`` while retaining both legacy fields.

This is the Python counterpart of MATLAB ``nt_import_markers.m``.
"""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from pathlib import Path
import re
from typing import Any

import numpy as np
import pandas as pd
from scipy.io import loadmat

from inpythotools.logmsg import logmsg
from .change_times import change_times
from .load_parameters import load_parameters
from .load_photometry import load_rwd_triggers, select_rwd_sync_triggers
from .marker_schema import (
    make_marker_record,
    marker_definition,
    normalize_marker_records,
    unknown_opto_parameters,
)
from .measures_schema import CURRENT_MEASURES_VERSION
from .photometry_folder import photometry_folder
from .session_path import session_path


IMPORT_OPTIONS = ("Noldus EPM log", "RWD log", "Laser log", "NewStim log")
StimIdProvider = Callable[[str], int | None]
TriggerShiftProvider = Callable[[], float | None]


def _missing_parameter(value: Any) -> bool:
    if value is None or (isinstance(value, np.ndarray) and value.size == 0):
        return True
    try:
        return bool(np.isnan(value))
    except (TypeError, ValueError):
        return False


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _set(obj: Any, name: str, value: Any) -> None:
    if isinstance(obj, Mapping):
        obj[name] = value
    elif isinstance(obj, pd.Series):
        obj.at[name] = value
    else:
        setattr(obj, name, value)


def _as_markers(value: Any, params: Any) -> list[dict[str, Any]]:
    return normalize_marker_records(value, params)


def _ensure_measures(record: Any, params: Any) -> dict[str, Any]:
    measures = _get(record, "measures", None)
    if not isinstance(measures, dict):
        measures = {}
    measures.pop("events", None)
    measures["markers"] = _as_markers(measures.get("markers", []), params)
    measures["measures_version"] = CURRENT_MEASURES_VERSION
    _set(record, "measures", measures)
    return measures


def _marker_definition(params: Any, marker: str) -> Mapping[str, Any] | None:
    return marker_definition(params, marker)


def insert_marker(
    markers: Any,
    time: float,
    marker: str,
    params: Any,
    *,
    stim_id_provider: StimIdProvider | None = None,
    duration: Any = np.nan,
    parameters: Mapping[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], int | None]:
    """Validate and chronologically insert one marker.

    Linked marker types carry a stimulus id, matching ``nt_insert_marker.m``.
    """
    records = _as_markers(markers, params)
    marker = str(marker)
    if not marker:
        return records, None

    definition = _marker_definition(params, marker)
    if definition is None:
        logmsg(f"Unknown marker {marker}. Not inserting the marker.")
        return records, None

    stim_id: int | None = None
    if bool(definition.get("linked", False)):
        suffix = marker[1:]
        if suffix.isdigit():
            stim_id = int(suffix)
        elif bool(_get(params, "neurotar", False)):
            stim_id = 1
        elif stim_id_provider is not None:
            stim_id = stim_id_provider(marker[0])
        if stim_id is None:
            logmsg(f"No stimulus id selected for linked marker {marker[0]}. Not inserting the marker.")
            return records, None
        marker = f"{marker[0]}{stim_id}"
    else:
        marker = marker[0]

    time = float(time)
    new_record = make_marker_record(
        time,
        marker,
        params,
        duration=duration,
        parameters=parameters,
    )
    existing = next(
        (item for item in records if item["time"] == time and item["marker"] == marker),
        None,
    )
    if existing is not None:
        if _missing_parameter(existing["duration"]) and not _missing_parameter(new_record["duration"]):
            existing["duration"] = new_record["duration"]
        for name, value in new_record["parameters"].items():
            if name not in existing["parameters"] or (
                _missing_parameter(existing["parameters"][name]) and not _missing_parameter(value)
            ):
                existing["parameters"][name] = value
        logmsg(f"Marker {marker} already present at t = {time:g}. Not inserting again")
        return records, stim_id

    records.append(new_record)
    records.sort(key=lambda item: item["time"])
    return records, stim_id


def _insert_events(
    markers: Any,
    events: pd.DataFrame,
    params: Any,
    *,
    stim_id_provider: StimIdProvider | None = None,
) -> list[dict[str, Any]]:
    records = _as_markers(markers, params)
    for event in events.itertuples(index=False):
        records, _ = insert_marker(
            records,
            float(event.time),
            str(event.code),
            params,
            stim_id_provider=stim_id_provider,
            duration=getattr(event, "duration", np.nan),
            parameters=getattr(event, "parameters", None),
        )
    return records


def _normalise_column(name: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def _find_column(table: pd.DataFrame, token: str) -> str | None:
    token = _normalise_column(token)
    for column in table.columns:
        if token in _normalise_column(column):
            return str(column)
    return None


def load_noldus_epm_events(
    record: Any,
    params: Any | None = None,
    *,
    filename: str | Path | None = None,
) -> pd.DataFrame:
    """Load elevated-plus-maze entries from a Noldus analysis workbook."""
    if params is None:
        params = load_parameters(record)
    if filename is None:
        folder, _ = session_path(record, params)
        filename = folder / f"{_get(record, 'subject', '')}_Noldus_behavioral_data.xlsx"
    filename = Path(filename)
    if not filename.exists():
        return pd.DataFrame(columns=["time", "code", "duration"])

    sheet = "Track-Arena 1-Subject 1"
    raw = pd.read_excel(filename, sheet_name=sheet, header=None)
    first_column = raw.iloc[:, 0].fillna("").astype(str)
    header_rows = np.flatnonzero(first_column.str.contains("Number of header lines:", regex=False))
    if header_rows.size == 0:
        logmsg(f"Cannot determine Noldus header length in {filename}")
        return pd.DataFrame(columns=["time", "code", "duration"])
    n_header_lines = int(float(raw.iloc[int(header_rows[0]), 1]))

    def metadata(label: str) -> Any:
        rows = np.flatnonzero(first_column.iloc[:n_header_lines].str.contains(label, regex=False))
        return None if rows.size == 0 else raw.iloc[int(rows[0]), 1]

    animal_id = metadata("Animal ID")
    if animal_id is not None and str(animal_id) != str(_get(record, "subject", "")):
        logmsg(f"Warning: Record subject {_get(record, 'subject', '')} and Noldus animal_id {animal_id} are not identical.")

    table = pd.read_excel(filename, sheet_name=sheet, header=n_header_lines - 2)
    table = table.dropna(how="all")
    trial_time_column = _find_column(table, "TrialTime")
    center_column = _find_column(table, "InZoneCenterCenterpoint")
    closed_column = _find_column(table, "InZoneClosedArmsCenterpoint")
    open_column = _find_column(table, "InZoneOpenArmsCenterpoint")
    if None in (trial_time_column, center_column, closed_column, open_column):
        return pd.DataFrame(columns=["time", "code", "duration"])

    offset = 0.0
    video_start = metadata("Video start time")
    trial_start = metadata("Start time")
    if video_start is not None and trial_start is not None:
        for day_first in (True, False):
            try:
                offset = (
                    pd.to_datetime(trial_start, dayfirst=day_first)
                    - pd.to_datetime(video_start, dayfirst=day_first)
                ).total_seconds()
                break
            except (TypeError, ValueError):
                continue

    trial_times = pd.to_numeric(table[trial_time_column], errors="coerce").to_numpy(dtype=float)
    event_rows: list[dict[str, Any]] = []
    for column, code in ((center_column, "m"), (closed_column, "c"), (open_column, "o")):
        values = pd.to_numeric(table[column], errors="coerce").fillna(0).to_numpy(dtype=float)
        for index in np.flatnonzero(np.diff(values) > 0) + 1:
            if np.isfinite(trial_times[index]):
                event_rows.append({"time": float(trial_times[index] + offset), "code": code})

    events = pd.DataFrame(event_rows, columns=["time", "code"]).sort_values("time").reset_index(drop=True)
    if events.empty:
        return pd.DataFrame(columns=["time", "code", "duration"])
    events["duration"] = events["time"].shift(-1) - events["time"]
    return events


def _parse_laser_datetime(text: str) -> datetime:
    return datetime.strptime(text.strip(), "%Y-%m-%d %H:%M:%S,%f")


def load_laser_events(
    record: Any,
    params: Any | None = None,
    *,
    filename: str | Path | None = None,
) -> pd.DataFrame:
    """Load the Raspberry Pi prey/opto laser log."""
    if params is None:
        params = load_parameters(record)
    if filename is None:
        folder, _ = session_path(record, params)
        filename = folder / f"{_get(record, 'sessionid', '')}_laser_triggers.csv"
    filename = Path(filename)
    if not filename.exists():
        logmsg(f"No laser trigger file for record {_get(record, 'sessionid', '')}")
        return pd.DataFrame(columns=["time", "code", "duration"])

    parsed: list[tuple[datetime, list[str], str]] = []
    for line in filename.read_text(encoding="utf-8-sig").splitlines():
        fields = line.split(",")
        if len(fields) < 2:
            continue
        try:
            timestamp = _parse_laser_datetime(",".join(fields[:2]))
        except ValueError:
            continue
        parsed.append((timestamp, fields, line))

    received = [timestamp for timestamp, _, line in parsed if "Received trigger" in line]
    if not received:
        logmsg(f"No trigger received in laser trigger log for record {_get(record, 'sessionid', '')}")
        return pd.DataFrame(columns=["time", "code", "duration"])
    if len(received) > 1:
        logmsg("Multiple triggers received in laser trigger log. Using the first trigger.")
    start = received[0]
    logmsg(
        f"Laser marker alignment: using received trigger at "
        f"{start.isoformat(sep=' ', timespec='milliseconds')} as source t = 0 s."
    )

    rows = []
    for timestamp, fields, line in parsed:
        if "Received trigger" in line or len(fields) < 5:
            continue
        try:
            rows.append(
                {
                    "time": (timestamp - start).total_seconds(),
                    "code": fields[3].strip(),
                    "duration": float(fields[4].strip()),
                }
            )
        except ValueError:
            continue
    return pd.DataFrame(rows, columns=["time", "code", "duration"]).sort_values("time").reset_index(drop=True)


def _mat_value(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _numeric_time_arrays(value: Any, path: str = "") -> list[np.ndarray]:
    arrays: list[np.ndarray] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            arrays.extend(_numeric_time_arrays(child, f"{path}.{key}".lower()))
    elif isinstance(value, (list, tuple)):
        for child in value:
            arrays.extend(_numeric_time_arrays(child, path))
    elif isinstance(value, np.ndarray) and value.dtype == object:
        for child in value.flat:
            arrays.extend(_numeric_time_arrays(child, path))
    elif "time" in path:
        try:
            array = np.asarray(value, dtype=float).reshape(-1)
        except (TypeError, ValueError):
            return arrays
        finite = array[np.isfinite(array)]
        if finite.size >= 2:
            arrays.append(finite)
    return arrays


def _newstim_duration(mat: Mapping[str, Any]) -> float | None:
    for container in (mat, _mat_value(mat, "saveScript", {})):
        for name in ("duration", "Duration", "dur"):
            value = _mat_value(container, name, None)
            if value is not None:
                try:
                    return float(np.asarray(value).reshape(-1)[0])
                except (TypeError, ValueError):
                    pass
    arrays = _numeric_time_arrays(_mat_value(mat, "MTI2", {}), "MTI2")
    if arrays:
        return max(float(np.nanmax(array) - np.nanmin(array)) for array in arrays)
    return None


def _script_fingerprint(value: Any) -> str:
    if isinstance(value, Mapping):
        return repr(sorted((str(key), _script_fingerprint(child)) for key, child in value.items()))
    if isinstance(value, np.ndarray):
        return repr((value.shape, [_script_fingerprint(child) for child in value.flat]))
    if hasattr(value, "_fieldnames"):
        return repr([(name, _script_fingerprint(getattr(value, name))) for name in value._fieldnames])
    return repr(value)


def load_newstim_triggers(
    record: Any,
    params: Any | None = None,
) -> tuple[np.ndarray, pd.DataFrame]:
    """Load NewStim ``stims.mat`` folders into triggers and typed events."""
    if params is None:
        params = load_parameters(record)
    folder, _ = session_path(record, params)
    stim_files = sorted(folder.glob("t00*/stims.mat"), key=lambda path: path.parent.stat().st_mtime)
    if not stim_files:
        logmsg("No NewStim folders")
        return np.array([], dtype=float), pd.DataFrame(columns=["time", "code", "duration"])

    scripts: dict[str, int] = {}
    rows = []
    for filename in stim_files:
        try:
            mat = loadmat(filename, squeeze_me=True, struct_as_record=False, simplify_cells=True)
            start = float(np.asarray(mat["start"]).reshape(-1)[0])
        except (KeyError, TypeError, ValueError, OSError) as error:
            logmsg(f"Could not read NewStim file {filename}: {error}")
            continue
        duration = _newstim_duration(mat)
        if duration is None:
            logmsg(f"Could not determine NewStim duration in {filename}")
            continue
        fingerprint = _script_fingerprint(mat.get("saveScript"))
        script_id = scripts.setdefault(fingerprint, len(scripts) + 1)
        rows.append({"time": start, "code": f"h{script_id}", "duration": duration})

    events = pd.DataFrame(rows, columns=["time", "code", "duration"]).sort_values("time").reset_index(drop=True)
    return events["time"].to_numpy(dtype=float), events


def _marker_for_id(params: Any, marker_id: str, default: str) -> str:
    table = _get(params, "markers", pd.DataFrame())
    if isinstance(table, pd.DataFrame) and "marker_id" in table:
        match = table.loc[table["marker_id"].astype(str) == marker_id, "marker"]
        if not match.empty:
            return str(match.iloc[0])
    logmsg(f"Cannot find marker motif {marker_id}. Using marker {default}.")
    return default


def _parse_rwd_parameter_value(value: Any) -> Any:
    """Convert numeric CSV values to numbers while retaining other strings."""
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        try:
            numeric = float(value)
        except ValueError:
            return value
    elif isinstance(value, (int, float, np.integer, np.floating)):
        numeric = float(value)
    else:
        return value
    return int(numeric) if np.isfinite(numeric) and numeric.is_integer() else numeric


def _normalize_rwd_parameter(name: Any, value: Any) -> tuple[str, Any]:
    """Return the case-insensitive internal name and SI value of a parameter."""
    parameter = str(name).strip().casefold()
    if parameter == "wavelength_nm":
        parameter = "wavelength"
        if isinstance(value, (int, float, np.integer, np.floating)):
            value = value * 1e-9
    return parameter, value


_KNOWN_RWD_EVENT_TYPES = {
    "event",
    "ignore",
    "ignored",
    "opto",
    "optogenetic",
    "optogenetics",
    "sync",
}


def load_rwd_parameters(photometry_folder: str | Path) -> pd.DataFrame:
    """Load optional timestamped per-input settings from ``Parameters.csv``.

    Timestamps are converted from RWD milliseconds to seconds, matching the
    unaligned event times returned by :func:`load_rwd_triggers`.
    """
    filename = Path(photometry_folder) / "Parameters.csv"
    columns = ["time", "input", "parameter", "value"]
    if not filename.exists():
        return pd.DataFrame(columns=columns)

    try:
        table = pd.read_csv(filename)
    except (OSError, pd.errors.ParserError) as error:
        logmsg(f"Could not read RWD parameter file {filename}: {error}")
        return pd.DataFrame(columns=columns)

    table.columns = [str(name).strip().casefold() for name in table.columns]
    required = {"timestamp", "input", "parameter", "value"}
    missing = sorted(required - set(table.columns))
    if missing:
        logmsg(f"Ignoring {filename}: missing column(s) {', '.join(missing)}")
        return pd.DataFrame(columns=columns)

    rows: list[dict[str, Any]] = []
    for row_number, row in table.iterrows():
        try:
            time = float(row["timestamp"]) / 1000.0
        except (TypeError, ValueError):
            logmsg(f"Ignoring invalid TimeStamp on row {row_number + 2} of {filename}")
            continue
        input_name = str(row["input"]).strip()
        value = _parse_rwd_parameter_value(row["value"])
        parameter, value = _normalize_rwd_parameter(row["parameter"], value)
        if not input_name or not parameter or value is None:
            logmsg(f"Ignoring incomplete row {row_number + 2} of {filename}")
            continue
        if parameter == "type" and str(value).strip().casefold() not in _KNOWN_RWD_EVENT_TYPES:
            logmsg(
                f"Unknown RWD event type {value!r} on row {row_number + 2} of "
                f"{filename}; events with this type will be treated as ordinary events."
            )
        rows.append(
            {"time": time, "input": input_name, "parameter": parameter, "value": value}
        )

    return (
        pd.DataFrame(rows, columns=columns)
        .sort_values("time", kind="stable")
        .reset_index(drop=True)
    )


def _rwd_event_input(code: Any) -> str:
    """Return the RWD input name underlying an InputN or TriggerN event."""
    match = re.fullmatch(r"(?:Input|Trigger)(\d+)", str(code), flags=re.IGNORECASE)
    return f"Input{match.group(1)}" if match else str(code)


def apply_rwd_parameters(events: pd.DataFrame, changes: pd.DataFrame) -> pd.DataFrame:
    """Attach the parameter state effective at each unaligned RWD event time."""
    annotated = events.copy()
    if annotated.empty:
        annotated["parameters"] = pd.Series(dtype=object)
        return annotated

    timelines: dict[str, dict[str, tuple[list[float], list[Any]]]] = {}
    for (input_name, parameter), rows in changes.groupby(
        ["input", "parameter"], sort=False
    ):
        timelines.setdefault(str(input_name).casefold(), {})[str(parameter)] = (
            rows["time"].astype(float).tolist(),
            rows["value"].tolist(),
        )

    parameter_states: list[dict[str, Any]] = []
    for event in annotated.itertuples(index=False):
        event_time = float(event.time)
        input_timelines = timelines.get(_rwd_event_input(event.code).casefold(), {})
        state: dict[str, Any] = {}
        for parameter, (times, values) in input_timelines.items():
            index = bisect_right(times, event_time) - 1
            if index >= 0:
                state[parameter] = values[index]
        parameter_states.append(state)
    annotated["parameters"] = parameter_states
    return annotated


def _rwd_event_type(event: Any) -> str:
    parameters = _get(event, "parameters", {})
    value = parameters.get("type") if isinstance(parameters, Mapping) else None
    if value is None:
        input_name = _rwd_event_input(_get(event, "code", ""))
        if input_name == "Input1":
            return "sync"
        return "opto" if input_name == "Input3" else "event"
    normalized = str(value).strip().casefold()
    if normalized in {"ignore", "ignored"}:
        return "ignore"
    if normalized in {"opto", "optogenetic", "optogenetics"}:
        return "opto"
    return normalized


def _rwd_event_parameters(event: Any) -> dict[str, Any]:
    parameters = _get(event, "parameters", {})
    return dict(parameters) if isinstance(parameters, Mapping) else {}


def import_noldus_epm(
    record: Any,
    params: Any,
    *,
    stim_id_provider: StimIdProvider | None = None,
) -> Any:
    measures = _ensure_measures(record, params)
    measures["markers"] = _insert_events(
        measures["markers"],
        load_noldus_epm_events(record, params),
        params,
        stim_id_provider=stim_id_provider,
    )
    return record


def import_laser(
    record: Any,
    params: Any,
    *,
    stim_id_provider: StimIdProvider | None = None,
) -> Any:
    measures = _ensure_measures(record, params)
    events = load_laser_events(record, params)
    markers = _as_markers(measures["markers"], params)
    multiplier = float(_get(params, "laser_time_multiplier", 1.0))
    logmsg(
        f"Laser marker import: {len(events)} event(s); source times and durations "
        f"are divided by laser_time_multiplier = {multiplier:.12g}."
    )
    for event in events.itertuples(index=False):
        time = float(event.time) / multiplier
        duration = float(event.duration) / multiplier
        additions: list[tuple[float, str, float, Mapping[str, Any] | None]] = []
        if event.code in ("p", "b"):
            additions.extend(
                ((time, "v", duration, None), (time + duration, "t", 0.0, None))
            )
        if event.code in ("o", "b"):
            additions.extend(
                (
                    (time, "1", duration, unknown_opto_parameters()),
                    (time + duration, "0", 0.0, None),
                )
            )
        for marker_time, marker, marker_duration, parameters in additions:
            markers, _ = insert_marker(
                markers,
                marker_time,
                marker,
                params,
                stim_id_provider=stim_id_provider,
                duration=marker_duration,
                parameters=parameters,
            )
    measures["markers"] = markers
    return record


def import_rwd(
    record: Any,
    params: Any,
    *,
    stim_id_provider: StimIdProvider | None = None,
) -> Any:
    measures = _ensure_measures(record, params)
    folder, found = photometry_folder(record, params)
    if not found or folder is None:
        return record
    rwd_triggers, events = load_rwd_triggers(folder, params)
    if events.empty:
        return record

    trigger_times = np.asarray(
        _get(measures, "trigger_times", []), dtype=float
    ).reshape(-1)
    if trigger_times.size == 0:
        logmsg("No record trigger_times found. Cannot align RWD events.")
        return record
    rwd_triggers = select_rwd_sync_triggers(events, rwd_triggers, trigger_times)

    parameter_changes = load_rwd_parameters(folder)
    events = apply_rwd_parameters(events, parameter_changes)
    event_types = events.apply(_rwd_event_type, axis=1)
    type_counts = event_types.value_counts().to_dict()
    type_summary = ", ".join(
        f"{name}={count}" for name, count in sorted(type_counts.items())
    )
    events = events.loc[~event_types.isin({"ignore", "sync"})].copy()
    event_types = event_types.loc[events.index]
    if events.empty:
        return record

    logmsg(
        f"RWD marker import from {folder}: {len(event_types)} retained event(s) "
        f"(raw event types: {type_summary or 'none'}), {rwd_triggers.size} RWD sync "
        f"pulse(s), and {trigger_times.size} master sync pulse(s)."
    )
    events = events.copy()
    events["time"], _, multiplier = change_times(
        events["time"].to_numpy(),
        rwd_triggers,
        trigger_times,
        diagnostic_label="RWD marker alignment",
    )
    events["duration"] = events["duration"].to_numpy(dtype=float) * multiplier
    if not events.empty:
        logmsg(
            f"RWD marker alignment: aligned event range "
            f"{events['time'].min():.6g} to {events['time'].max():.6g} s; "
            f"durations multiplied by {multiplier:.12g}."
        )

    newstim_triggers, newstim_events = load_newstim_triggers(record, params)
    stim_events = (
        events.loc[events["code"] == "Trigger2"].copy()
        if newstim_triggers.size
        else events.loc[event_types != "opto"].copy()
    )
    markers = _as_markers(measures["markers"], params)
    for event in events.loc[event_types == "opto"].itertuples(index=False):
        opto_parameters = unknown_opto_parameters()
        opto_parameters.update(_rwd_event_parameters(event))
        for marker_time, marker, marker_duration, parameters in (
            (
                float(event.time),
                _marker_for_id(params, "opto_on", "1"),
                float(event.duration),
                opto_parameters,
            ),
            (
                float(event.time + event.duration),
                _marker_for_id(params, "opto_off", "0"),
                0.0,
                None,
            ),
        ):
            markers, _ = insert_marker(
                markers,
                marker_time,
                marker,
                params,
                stim_id_provider=stim_id_provider,
                duration=marker_duration,
                parameters=parameters,
            )

    rwd_diff = np.diff(stim_events["time"].to_numpy(dtype=float))
    newstim_diff = np.diff(newstim_triggers)
    matching_newstim = (
        newstim_triggers.size > 0
        and len(stim_events) == len(newstim_events)
        and rwd_diff.size == newstim_diff.size
        and (rwd_diff.size == 0 or np.max(np.abs(rwd_diff - newstim_diff)) < 0.020)
    )
    maximum_interval_difference = (
        float(np.max(np.abs(rwd_diff - newstim_diff)))
        if rwd_diff.size and rwd_diff.size == newstim_diff.size
        else np.nan
    )
    interval_detail = (
        f", maximum interval difference {1000 * maximum_interval_difference:.6g} ms"
        if np.isfinite(maximum_interval_difference)
        else ""
    )
    logmsg(
        f"RWD/NewStim marker match: {len(stim_events)} RWD stimulus event(s), "
        f"{len(newstim_events)} NewStim event(s){interval_detail}; "
        f"match={'yes' if matching_newstim else 'no'}."
    )
    if matching_newstim:
        for rwd_event, newstim_event in zip(stim_events.itertuples(index=False), newstim_events.itertuples(index=False)):
            code = str(newstim_event.code)
            stim_duration = float(newstim_event.duration) * multiplier
            for marker_time, marker, marker_duration in (
                (float(rwd_event.time), code, stim_duration),
                (float(rwd_event.time) + stim_duration, f"t{code[1:]}", 0.0),
            ):
                markers, _ = insert_marker(
                    markers,
                    marker_time,
                    marker,
                    params,
                    stim_id_provider=stim_id_provider,
                    duration=marker_duration,
                    parameters=(
                        _rwd_event_parameters(rwd_event)
                        if marker_time == float(rwd_event.time)
                        else None
                    ),
                )
    else:
        unique_codes = {code: index + 1 for index, code in enumerate(sorted(stim_events["code"].astype(str).unique()))}
        for event in stim_events.itertuples(index=False):
            markers, _ = insert_marker(
                markers,
                float(event.time),
                f"o{unique_codes[str(event.code)]}",
                params,
                stim_id_provider=stim_id_provider,
                duration=float(event.duration),
                parameters=_rwd_event_parameters(event),
            )

    measures["markers"] = markers
    return record


def import_newstim(
    record: Any,
    params: Any,
    *,
    stim_id_provider: StimIdProvider | None = None,
    trigger_shift_provider: TriggerShiftProvider | None = None,
) -> Any:
    measures = _ensure_measures(record, params)
    triggers, events = load_newstim_triggers(record, params)
    if triggers.size == 0 or events.empty:
        logmsg("No NewStim triggers to import.")
        return record

    master_triggers = np.asarray(_get(measures, "trigger_times", []), dtype=float).reshape(-1)
    shift = 0.0
    if master_triggers.size == 0 or (master_triggers.size == 1 and master_triggers[0] == 0):
        selected = trigger_shift_provider() if trigger_shift_provider is not None else 0.0
        if selected is None:
            return record
        shift = float(selected)
    alignment_targets = master_triggers if master_triggers.size else np.array([0.0])
    changed_times, _, multiplier = change_times(
        events["time"].to_numpy(dtype=float),
        triggers,
        alignment_targets,
        diagnostic_label="NewStim marker alignment",
    )
    logmsg(
        f"NewStim marker alignment: {len(events)} event(s), manual shift "
        f"{shift:.9g} s, durations multiplied by {multiplier:.12g}."
    )

    markers = _as_markers(measures["markers"], params)
    for event, time in zip(events.itertuples(index=False), changed_times):
        code = str(event.code)
        duration = float(event.duration) * multiplier
        for marker_time, marker, marker_duration in (
            (float(time) + shift, code, duration),
            (float(time) + shift + duration, f"t{code[1:]}", 0.0),
        ):
            markers, _ = insert_marker(
                markers,
                marker_time,
                marker,
                params,
                stim_id_provider=stim_id_provider,
                duration=marker_duration,
            )
    measures["markers"] = markers
    return record


def import_markers(
    record: Any,
    option: str | Sequence[str] | None = None,
    *,
    params: Any | None = None,
    stim_id_provider: StimIdProvider | None = None,
    trigger_shift_provider: TriggerShiftProvider | None = None,
) -> Any:
    """Import one or more supported marker log types into ``record``.

    With no option, all supported sources are attempted. The tracking window
    supplies the user's checkbox selections explicitly.
    """
    if record is None:
        return record
    if params is None:
        params = load_parameters(record)
    options = list(IMPORT_OPTIONS) if option is None else ([option] if isinstance(option, str) else list(option))
    unknown = [name for name in options if name not in IMPORT_OPTIONS]
    if unknown:
        raise ValueError(f"Unknown marker import option(s): {', '.join(unknown)}")

    dispatch = {
        "Noldus EPM log": import_noldus_epm,
        "RWD log": import_rwd,
        "Laser log": import_laser,
        "NewStim log": import_newstim,
    }
    _ensure_measures(record, params)
    for name in options:
        kwargs: dict[str, Any] = {"stim_id_provider": stim_id_provider}
        if name == "NewStim log":
            kwargs["trigger_shift_provider"] = trigger_shift_provider
        record = dispatch[name](record, params, **kwargs)
    return record


__all__ = [
    "IMPORT_OPTIONS",
    "apply_rwd_parameters",
    "import_markers",
    "insert_marker",
    "load_laser_events",
    "load_newstim_triggers",
    "load_noldus_epm_events",
    "load_rwd_parameters",
]
