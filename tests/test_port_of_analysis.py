from inpythotools import load_mat_database
from novitrack import analyse_nttestrecord, results_nttestrecord
from novitrack.get_ethogram import get_ethogram
from novitrack.plot_photometry import _channel_label
import numpy as np
from pathlib import Path
import importlib

analyse_module = importlib.import_module("novitrack.analyse_nttestrecord")


def test_ethogram_uses_white_background():
    record = {
        "sessionid": "example",
        "measures": {
            "markers": [
                {"marker": "a", "time": 0.0},
                {"marker": "b", "time": 1.0},
            ],
            "min_time": 0.0,
            "max_time": 2.0,
        },
    }
    params = {
        "markers": [
            {"marker": "a", "behavior": True, "description": "approach", "color": [1.0, 0.0, 0.0]},
            {"marker": "b", "behavior": True, "description": "back", "color": [0.0, 1.0, 0.0]},
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


def test_analysis():
    filename = Path(__file__).resolve().parent.parent / "test_data" / "nttestdb_examples.mat"
    db = load_mat_database(filename)
#    record = db.iloc[-1].to_dict()
    record = db.iloc[1]
    out = analyse_nttestrecord(record, verbose=False)
    results = results_nttestrecord(out, show=False)
    return results


if __name__ == "__main__":
    test_analysis()
