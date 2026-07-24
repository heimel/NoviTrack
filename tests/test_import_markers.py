from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import novitrack.import_markers as marker_import


def _params(marker_rows, **kwargs):
    defaults = {
        "markers": pd.DataFrame(marker_rows),
        "neurotar": True,
        "laser_time_multiplier": 1.0,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_insert_marker_validates_linked_markers_sorts_and_deduplicates():
    params = _params(
        [
            {"marker_id": "start", "marker": "o", "linked": True},
            {"marker_id": "idle", "marker": "i", "linked": False},
        ]
    )
    markers = [{"time": 3.0, "marker": "i"}]

    markers, stim_id = marker_import.insert_marker(markers, 2.0, "o2", params)
    markers, _ = marker_import.insert_marker(markers, 2.0, "o2", params)
    markers, _ = marker_import.insert_marker(markers, 1.0, "unknown", params)

    assert stim_id == 2
    assert markers == [
        {"time": 2.0, "marker": "o2"},
        {"time": 3.0, "marker": "i"},
    ]


def test_load_laser_events_uses_received_trigger_as_time_zero(tmp_path):
    filename = tmp_path / "session_laser_triggers.csv"
    filename.write_text(
        "\n".join(
            [
                "2026-01-02 12:00:00,000,INFO,Received trigger,0",
                "2026-01-02 12:00:02,500,INFO,p,1.5",
                "2026-01-02 12:00:04,000,INFO,o,2",
            ]
        ),
        encoding="utf-8",
    )

    events = marker_import.load_laser_events({}, filename=filename)

    assert events.to_dict(orient="records") == [
        {"time": 2.5, "code": "p", "duration": 1.5},
        {"time": 4.0, "code": "o", "duration": 2.0},
    ]


def test_import_laser_translates_prey_and_opto_events(monkeypatch):
    params = _params(
        [
            {"marker_id": "virtual", "marker": "v", "linked": True},
            {"marker_id": "stop", "marker": "t", "linked": True},
            {"marker_id": "opto_on", "marker": "1", "linked": False},
            {"marker_id": "opto_off", "marker": "0", "linked": False},
        ],
        laser_time_multiplier=2.0,
    )
    record = {"measures": {"markers": []}}
    monkeypatch.setattr(
        marker_import,
        "load_laser_events",
        lambda *args, **kwargs: pd.DataFrame(
            [{"time": 4.0, "code": "b", "duration": 2.0}]
        ),
    )

    marker_import.import_laser(record, params)

    assert record["measures"]["markers"] == [
        {"time": 2.0, "marker": "v1"},
        {"time": 2.0, "marker": "1"},
        {"time": 3.0, "marker": "t1"},
        {"time": 3.0, "marker": "0"},
    ]


def test_load_noldus_epm_events_detects_zone_entries_and_video_offset(monkeypatch, tmp_path):
    filename = tmp_path / "mouse_Noldus_behavioral_data.xlsx"
    filename.touch()
    raw = pd.DataFrame(
        [
            ["Number of header lines:", 6],
            ["Animal ID", "mouse"],
            ["Video start time", "24/07/2026 10:00:00"],
            ["Start time", "24/07/2026 10:00:05"],
            [None, None],
            [None, None],
        ]
    )
    table = pd.DataFrame(
        {
            "Trial Time": [0, 1, 2, 3],
            "In zone(Center - Center-point)": [0, 1, 0, 0],
            "In zone(Closed Arms - Center-point)": [1, 0, 1, 0],
            "In zone(Open Arms - Center-point)": [0, 0, 0, 1],
        }
    )
    monkeypatch.setattr(
        marker_import.pd,
        "read_excel",
        lambda *args, **kwargs: raw if kwargs.get("header") is None else table,
    )

    events = marker_import.load_noldus_epm_events(
        {"subject": "mouse"},
        SimpleNamespace(),
        filename=filename,
    )

    assert events[["time", "code"]].to_dict(orient="records") == [
        {"time": 6.0, "code": "m"},
        {"time": 7.0, "code": "c"},
        {"time": 8.0, "code": "o"},
    ]
    assert events["duration"].iloc[:2].tolist() == [1.0, 1.0]
    assert np.isnan(events["duration"].iloc[-1])


def test_import_newstim_aligns_events_to_master_time(monkeypatch):
    params = _params(
        [
            {"marker_id": "overhead", "marker": "h", "linked": True},
            {"marker_id": "stop", "marker": "t", "linked": True},
        ]
    )
    record = {"measures": {"markers": [], "trigger_times": np.array([100.0])}}
    monkeypatch.setattr(
        marker_import,
        "load_newstim_triggers",
        lambda *args, **kwargs: (
            np.array([10.0]),
            pd.DataFrame([{"time": 10.0, "code": "h1", "duration": 5.0}]),
        ),
    )

    marker_import.import_newstim(record, params)

    assert record["measures"]["markers"] == [
        {"time": pytest.approx(100.0), "marker": "h1"},
        {"time": pytest.approx(105.0), "marker": "t1"},
    ]


def test_import_rwd_adds_opto_and_numbered_event_markers(monkeypatch, tmp_path):
    params = _params(
        [
            {"marker_id": "start", "marker": "o", "linked": True},
            {"marker_id": "opto_on", "marker": "1", "linked": False},
            {"marker_id": "opto_off", "marker": "0", "linked": False},
        ]
    )
    record = {"measures": {"markers": [], "trigger_times": np.array([0.0])}}
    events = pd.DataFrame(
        [
            {"time": 10.0, "code": "Trigger1", "duration": 0.0},
            {"time": 20.0, "code": "Input3", "duration": 2.0},
            {"time": 30.0, "code": "Trigger2", "duration": 0.0},
        ]
    )
    monkeypatch.setattr(marker_import, "photometry_folder", lambda *args: (tmp_path, True))
    monkeypatch.setattr(
        marker_import,
        "load_rwd_triggers",
        lambda *args: (np.array([10.0]), events),
    )
    monkeypatch.setattr(
        marker_import,
        "load_newstim_triggers",
        lambda *args: (np.array([]), pd.DataFrame()),
    )

    marker_import.import_rwd(record, params)

    assert record["measures"]["markers"] == [
        {"time": pytest.approx(0.0), "marker": "o1"},
        {"time": pytest.approx(10.0), "marker": "1"},
        {"time": pytest.approx(12.0), "marker": "0"},
        {"time": pytest.approx(20.0), "marker": "o2"},
    ]


def test_import_markers_rejects_unknown_option():
    with pytest.raises(ValueError, match="Unknown marker import option"):
        marker_import.import_markers({}, "Other log", params=SimpleNamespace())
