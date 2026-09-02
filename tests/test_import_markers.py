from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import novitrack.import_markers as marker_import
from novitrack.measures_schema import CURRENT_MEASURES_VERSION


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
    assert [(marker["time"], marker["marker"], marker["marker_id"]) for marker in markers] == [
        (2.0, "o2", "start"),
        (3.0, "i", "idle"),
    ]
    assert markers[0]["parameters"] == {"stimulus_id": 2}
    assert markers[1]["parameters"] == {}
    assert all(np.isnan(marker["duration"]) for marker in markers)


def test_load_laser_events_uses_received_trigger_as_time_zero(tmp_path, capsys):
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
    assert (
        "using received trigger at 2026-01-02 12:00:00.000 as source t = 0 s"
        in capsys.readouterr().out
    )


def test_import_laser_translates_prey_and_opto_events(monkeypatch, capsys):
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

    markers = record["measures"]["markers"]
    assert [(marker["time"], marker["marker"], marker["marker_id"]) for marker in markers] == [
        (2.0, "v1", "virtual"),
        (2.0, "1", "opto_on"),
        (3.0, "t1", "stop"),
        (3.0, "0", "opto_off"),
    ]
    assert [marker["duration"] for marker in markers] == [1.0, 1.0, 0.0, 0.0]
    assert markers[0]["parameters"] == {"stimulus_id": 1}
    assert markers[2]["parameters"] == {"stimulus_id": 1}
    assert set(markers[1]["parameters"]) == {"frequency", "pulse_width", "power"}
    assert all(np.isnan(value) for value in markers[1]["parameters"].values())
    assert markers[3]["parameters"] == {}
    assert record["measures"]["measures_version"] == CURRENT_MEASURES_VERSION
    assert "divided by laser_time_multiplier = 2" in capsys.readouterr().out


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

    markers = record["measures"]["markers"]
    assert [marker["time"] for marker in markers] == pytest.approx([100.0, 105.0])
    assert [marker["marker"] for marker in markers] == ["h1", "t1"]
    assert [marker["marker_id"] for marker in markers] == ["overhead", "stop"]
    assert [marker["duration"] for marker in markers] == pytest.approx([5.0, 0.0])
    assert [marker["parameters"] for marker in markers] == [
        {"stimulus_id": 1},
        {"stimulus_id": 1},
    ]


def test_import_rwd_adds_opto_and_numbered_event_markers(monkeypatch, tmp_path, capsys):
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

    markers = record["measures"]["markers"]
    assert [marker["time"] for marker in markers] == pytest.approx([10.0, 12.0, 20.0])
    assert [marker["marker"] for marker in markers] == ["1", "0", "o1"]
    assert [marker["marker_id"] for marker in markers] == [
        "opto_on",
        "opto_off",
        "start",
    ]
    assert [marker["duration"] for marker in markers] == pytest.approx([2.0, 0.0, 0.0])
    assert set(markers[0]["parameters"]) == {"frequency", "pulse_width", "power"}
    assert all(np.isnan(value) for value in markers[0]["parameters"].values())
    assert markers[1]["parameters"] == {}
    assert markers[2]["parameters"] == {"stimulus_id": 1}

    output = capsys.readouterr().out
    assert "1 RWD sync pulse(s), and 1 master sync pulse(s)" in output
    assert "matched 1/1 source sync pulse(s) to 1/1 master sync pulse(s)" in output
    assert "clock multiplier 1" in output
    assert "only one sync-pulse pair is available" in output
    assert "aligned event range 10 to 20 s" in output
    assert "RWD/NewStim marker match" in output


def test_import_rwd_applies_timestamped_input_parameters(monkeypatch, tmp_path):
    params = _params(
        [
            {"marker_id": "start", "marker": "o", "linked": True},
            {"marker_id": "opto_on", "marker": "1", "linked": False},
            {"marker_id": "opto_off", "marker": "0", "linked": False},
        ]
    )
    (tmp_path / "Parameters.csv").write_text(
        "\n".join(
            [
                "TimeStamp,Input,Parameter,Value",
                "0,Input1,TYPE,sync",
                "0,Input4,Type,ignore",
                "0,Input2,tYpE,opto",
                "0,Input2,Wavelength_nm,1000",
                "0,Input2,Frequency,5",
                "0,Input2,mode,pulsed",
                "3000,Input2,frequency,10",
            ]
        ),
        encoding="utf-8",
    )
    record = {"measures": {"markers": [], "trigger_times": np.array([0.0])}}
    events = pd.DataFrame(
        [
            {"time": 0.0, "code": "Trigger1", "duration": 0.0},
            {"time": 1.0, "code": "Input2", "duration": 1.0},
            {"time": 2.0, "code": "Input4", "duration": 0.0},
            {"time": 3.0, "code": "Input2", "duration": 1.0},
        ]
    )
    monkeypatch.setattr(marker_import, "photometry_folder", lambda *args: (tmp_path, True))
    monkeypatch.setattr(
        marker_import,
        "load_rwd_triggers",
        lambda *args: (np.array([0.0]), events),
    )
    monkeypatch.setattr(
        marker_import,
        "load_newstim_triggers",
        lambda *args: (np.array([]), pd.DataFrame()),
    )

    marker_import.import_rwd(record, params)

    markers = record["measures"]["markers"]
    assert [marker["marker_id"] for marker in markers] == [
        "opto_on",
        "opto_off",
        "opto_on",
        "opto_off",
    ]
    assert [marker["time"] for marker in markers] == pytest.approx([1, 2, 3, 4])
    assert markers[0]["parameters"]["frequency"] == 5
    assert markers[2]["parameters"]["frequency"] == 10
    assert markers[0]["parameters"]["wavelength"] == pytest.approx(1e-6)
    assert markers[0]["parameters"]["mode"] == "pulsed"
    assert markers[0]["parameters"]["type"] == "opto"
    assert np.isnan(markers[0]["parameters"]["pulse_width"])
    assert np.isnan(markers[0]["parameters"]["power"])


def test_load_rwd_parameters_is_optional(tmp_path):
    parameters = marker_import.load_rwd_parameters(tmp_path)

    assert parameters.empty
    assert parameters.columns.tolist() == ["time", "input", "parameter", "value"]


def test_load_rwd_parameters_accepts_case_insensitive_headers_and_names(tmp_path):
    (tmp_path / "Parameters.csv").write_text(
        "timestamp,INPUT,parameter,value\n0,Input3,wavelength_nm,470\n"
        "1000,Input3,Wavelength_nm,560\n1000,Input3,PULSE_WIDTH,0.01\n",
        encoding="utf-8",
    )

    parameters = marker_import.load_rwd_parameters(tmp_path)

    assert parameters["parameter"].tolist() == [
        "wavelength",
        "wavelength",
        "pulse_width",
    ]
    assert parameters["value"].tolist() == pytest.approx([470e-9, 560e-9, 0.01])


def test_import_markers_rejects_unknown_option():
    with pytest.raises(ValueError, match="Unknown marker import option"):
        marker_import.import_markers({}, "Other log", params=SimpleNamespace())
