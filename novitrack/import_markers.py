"""Import NoviTrack markers from external acquisition and analysis logs.

This is the Python counterpart of MATLAB ``nt_import_markers.m``.
"""

from __future__ import annotations

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
from .load_photometry import load_rwd_triggers
from .photometry_folder import photometry_folder
from .session_path import session_path


IMPORT_OPTIONS = ("Noldus EPM log", "RWD log", "Laser log", "NewStim log")
StimIdProvider = Callable[[str], int | None]
TriggerShiftProvider = Callable[[], float | None]


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


def _as_markers(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, pd.DataFrame):
        value = value.to_dict(orient="records")
    elif isinstance(value, Mapping):
        value = [value]
    try:
        markers = [
            {
                "time": float(_get(marker, "time", np.nan)),
                "marker": str(_get(marker, "marker", "")),
            }
            for marker in value
        ]
    except TypeError:
        return []
    return sorted(markers, key=lambda marker: marker["time"])


def _ensure_measures(record: Any) -> dict[str, Any]:
    measures = _get(record, "measures", None)
    if not isinstance(measures, dict):
        measures = {}
    measures.pop("events", None)
    measures.setdefault("markers", [])
    _set(record, "measures", measures)
    return measures


def _marker_definition(params: Any, marker: str) -> Mapping[str, Any] | None:
    table = _get(params, "markers", pd.DataFrame())
    if not isinstance(table, pd.DataFrame) or table.empty or "marker" not in table:
        return None
    match = table.loc[table["marker"].astype(str) == marker[0]]
    return None if match.empty else match.iloc[0].to_dict()


def insert_marker(
    markers: Any,
    time: float,
    marker: str,
    params: Any,
    *,
    stim_id_provider: StimIdProvider | None = None,
) -> tuple[list[dict[str, Any]], int | None]:
    """Validate and chronologically insert one marker.

    Linked marker types carry a stimulus id, matching ``nt_insert_marker.m``.
    """
    records = _as_markers(markers)
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
    if any(item["time"] == time and item["marker"] == marker for item in records):
        logmsg(f"Marker {marker} already present at t = {time:g}. Not inserting again")
        return records, stim_id

    records.append({"time": time, "marker": marker})
    records.sort(key=lambda item: item["time"])
    return records, stim_id


def _insert_events(
    markers: Any,
    events: pd.DataFrame,
    params: Any,
    *,
    stim_id_provider: StimIdProvider | None = None,
) -> list[dict[str, Any]]:
    records = _as_markers(markers)
    for event in events.itertuples(index=False):
        records, _ = insert_marker(
            records,
            float(event.time),
            str(event.code),
            params,
            stim_id_provider=stim_id_provider,
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


def import_noldus_epm(
    record: Any,
    params: Any,
    *,
    stim_id_provider: StimIdProvider | None = None,
) -> Any:
    measures = _ensure_measures(record)
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
    measures = _ensure_measures(record)
    events = load_laser_events(record, params)
    markers = _as_markers(measures["markers"])
    multiplier = float(_get(params, "laser_time_multiplier", 1.0))
    for event in events.itertuples(index=False):
        time = float(event.time) / multiplier
        duration = float(event.duration) / multiplier
        additions = []
        if event.code in ("p", "b"):
            additions.extend(((time, "v"), (time + duration, "t")))
        if event.code in ("o", "b"):
            additions.extend(((time, "1"), (time + duration, "0")))
        for marker_time, marker in additions:
            markers, _ = insert_marker(
                markers,
                marker_time,
                marker,
                params,
                stim_id_provider=stim_id_provider,
            )
    measures["markers"] = markers
    return record


def import_rwd(
    record: Any,
    params: Any,
    *,
    stim_id_provider: StimIdProvider | None = None,
) -> Any:
    measures = _ensure_measures(record)
    folder, found = photometry_folder(record, params)
    if not found or folder is None:
        return record
    rwd_triggers, events = load_rwd_triggers(folder, params)
    if events.empty:
        return record

    trigger_times = np.asarray(_get(measures, "trigger_times", []), dtype=float).reshape(-1)
    if trigger_times.size == 0:
        logmsg("No record trigger_times found. Cannot align RWD events.")
        return record
    events = events.copy()
    events["time"], _, multiplier = change_times(events["time"].to_numpy(), rwd_triggers, trigger_times)
    events["duration"] = events["duration"].to_numpy(dtype=float) * multiplier

    newstim_triggers, newstim_events = load_newstim_triggers(record, params)
    stim_events = events.loc[events["code"] == "Trigger2"].copy() if newstim_triggers.size else events.copy()
    markers = _as_markers(measures["markers"])
    for event in events.loc[events["code"] == "Input3"].itertuples(index=False):
        for marker_time, marker in (
            (float(event.time), _marker_for_id(params, "opto_on", "1")),
            (float(event.time + event.duration), _marker_for_id(params, "opto_off", "0")),
        ):
            markers, _ = insert_marker(markers, marker_time, marker, params, stim_id_provider=stim_id_provider)

    rwd_diff = np.diff(stim_events["time"].to_numpy(dtype=float))
    newstim_diff = np.diff(newstim_triggers)
    matching_newstim = (
        newstim_triggers.size > 0
        and len(stim_events) == len(newstim_events)
        and rwd_diff.size == newstim_diff.size
        and (rwd_diff.size == 0 or np.max(np.abs(rwd_diff - newstim_diff)) < 0.020)
    )
    if matching_newstim:
        for rwd_event, newstim_event in zip(stim_events.itertuples(index=False), newstim_events.itertuples(index=False)):
            code = str(newstim_event.code)
            for marker_time, marker in (
                (float(rwd_event.time), code),
                (float(rwd_event.time) + float(newstim_event.duration) * multiplier, f"t{code[1:]}"),
            ):
                markers, _ = insert_marker(markers, marker_time, marker, params, stim_id_provider=stim_id_provider)
    else:
        stim_events = stim_events.loc[stim_events["code"] != "Input3"]
        unique_codes = {code: index + 1 for index, code in enumerate(sorted(stim_events["code"].astype(str).unique()))}
        for event in stim_events.itertuples(index=False):
            markers, _ = insert_marker(
                markers,
                float(event.time),
                f"o{unique_codes[str(event.code)]}",
                params,
                stim_id_provider=stim_id_provider,
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
    measures = _ensure_measures(record)
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
    changed_times, _, multiplier = change_times(events["time"].to_numpy(dtype=float), triggers, master_triggers if master_triggers.size else [0])

    markers = _as_markers(measures["markers"])
    for event, time in zip(events.itertuples(index=False), changed_times):
        code = str(event.code)
        for marker_time, marker in (
            (float(time) + shift, code),
            (float(time) + shift + float(event.duration) * multiplier, f"t{code[1:]}"),
        ):
            markers, _ = insert_marker(markers, marker_time, marker, params, stim_id_provider=stim_id_provider)
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
    _ensure_measures(record)
    for name in options:
        kwargs: dict[str, Any] = {"stim_id_provider": stim_id_provider}
        if name == "NewStim log":
            kwargs["trigger_shift_provider"] = trigger_shift_provider
        record = dispatch[name](record, params, **kwargs)
    return record


__all__ = [
    "IMPORT_OPTIONS",
    "import_markers",
    "insert_marker",
    "load_laser_events",
    "load_newstim_triggers",
    "load_noldus_epm_events",
]
