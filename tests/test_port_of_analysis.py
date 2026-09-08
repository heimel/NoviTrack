from inpythotools import load_mat_database
from novitrack import analyse_nttestrecord, results_nttestrecord
from novitrack.get_ethogram import get_ethogram
from novitrack.plot_photometry import _channel_label, channel_metadata_lines
from novitrack.plot_session_summary import plot_session_summary
import numpy as np
from pathlib import Path
import importlib

analyse_module = importlib.import_module("novitrack.analyse_nttestrecord")
results_module = importlib.import_module("novitrack.results_nttestrecord")


def test_ethogram_uses_white_background():
    record = {
        "sessionid": "example",
        "measures": {
            "markers": [
                {"marker_id": "approach", "duration": np.nan, "parameters": {}, "time": 0.0},
                {"marker_id": "back", "duration": np.nan, "parameters": {}, "time": 1.0},
            ],
            "min_time": 0.0,
            "max_time": 2.0,
        },
    }
    params = {
        "markers": [
            {"marker_id": "approach", "behavior": True, "description": "approach", "color": [1.0, 0.0, 0.0]},
            {"marker_id": "back", "behavior": True, "description": "back", "color": [0.0, 1.0, 0.0]},
        ],
        "show_markers": True,
    }

    _ethogram, _t, _motifs, ax = get_ethogram(record, show=True, params=params)
    assert ax.images[0].cmap(0)[:3] == (1.0, 1.0, 1.0)


def test_photometry_channel_label_accepts_matlab_empty_arrays():
    channel = {
        "channel": "channel2",
        "location": np.array([]),
        "green_sensor": np.array(["G", "C", "a", "M", "P"]),
    }

    assert _channel_label(channel) == "GCaMP"


def test_channel_metadata_lines_include_location_and_sensors():
    channel = {
        "channel": "Channel1",
        "hemisphere": "left",
        "location": "central iSC",
        "green_sensor": "dLight3.8",
        "red_sensor": "jRGECO1a",
    }

    assert channel_metadata_lines(channel) == [
        "Channel1",
        "left central iSC",
        "green = dLight3.8",
        "red = jRGECO1a",
    ]


def test_missing_session_path_warning_points_to_local_config(monkeypatch, tmp_path):
    errors = []
    logs = []
    monkeypatch.setattr(analyse_module, "errormsg", errors.append)
    monkeypatch.setattr(analyse_module, "logmsg", logs.append)
    monkeypatch.setattr(analyse_module, "_MISSING_SESSION_PATH_DIALOG_SHOWN", False)

    analyse_module._warn_missing_session_path(tmp_path / "missing-session")
    analyse_module._warn_missing_session_path(tmp_path / "missing-session")

    assert len(errors) == 1
    assert len(logs) == 1
    assert "Session path" in errors[0]
    assert "does not exist" in errors[0]
    assert "networkpath" in errors[0]
    assert "from inpythotools import edit_local_config" in errors[0]
    assert "edit_local_config()" in errors[0]


def test_missing_position_tracking_is_stored_and_clears_stale_session_measures():
    measures = {
        "session_fraction_running_forward": 0.2,
        "session_start_running_forward_per_min": 3.0,
    }

    available = analyse_module._set_position_tracking_status(
        measures,
        {"X": [np.nan], "Y": [np.nan]},
    )

    assert available is False
    assert measures["position_tracking_available"] is False
    assert "session_fraction_running_forward" not in measures
    assert "session_start_running_forward_per_min" not in measures


def test_session_summary_is_suppressed_without_position_tracking():
    record = {
        "measures": {
            "position_tracking_available": False,
            "session_fraction_running_forward": 0.2,
            "session_start_running_forward_per_min": 3.0,
            "session_fraction_moving_backward": 0.1,
            "session_start_moving_backward_per_min": 1.0,
        }
    }

    assert plot_session_summary(record) is None


def test_results_infers_position_tracking_status_for_legacy_measures(monkeypatch):
    record = {"measures": {"session_fraction_running_forward": 0.0}}
    monkeypatch.setattr(
        results_module,
        "load_tracking_data",
        lambda record, params, save_cache: ({"X": [np.nan], "Y": [np.nan]}, np.array([])),
    )

    updated = results_module._ensure_position_tracking_status(record, object())

    assert updated["measures"]["position_tracking_available"] is False
    assert "position_tracking_available" not in record["measures"]


def test_analysis():
    filename = Path(__file__).resolve().parent.parent / "test_data" / "nttestdb_examples.mat"
    db = load_mat_database(filename)
    for record_index in (0, 1):
        out = analyse_nttestrecord(db.iloc[record_index], verbose=False)
        assert "position_tracking_available" in out["measures"]
        results = results_nttestrecord(out, show=False)
        assert results


if __name__ == "__main__":
    test_analysis()
