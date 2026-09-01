from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from novitrack.load_photometry import (
    _import_rwd_markers,
    parse_channels,
    select_rwd_sync_triggers,
)
from novitrack.measures_schema import CURRENT_MEASURES_VERSION


@pytest.mark.parametrize("comment", [None, "", np.array([])])
def test_parse_channels_accepts_empty_comment_representations(comment):
    assert parse_channels(comment) == {}


def test_parse_channels_accepts_native_string():
    assert parse_channels("channel1 = signal, channel2 = isosbestic.") == {
        "Channel1": "signal",
        "Channel2": "isosbestic",
    }


def test_sync_selection_recovers_long_input1_pulse_when_fit_is_good(capsys):
    events = pd.DataFrame(
        [
            {"time": 35.560552, "code": "Trigger1", "duration": 0.0},
            {"time": 1480.527216, "code": "Trigger1", "duration": 0.0},
            {"time": 6218.528582, "code": "Input1", "duration": 1.565940},
            {"time": 6230.915211, "code": "Trigger1", "duration": 0.0},
        ]
    )
    short_triggers = np.array([35.560552, 1480.527216, 6230.915211])
    master_triggers = np.array([0.0, 1444.962165, 6182.984461, 6195.363711])

    selected = select_rwd_sync_triggers(events, short_triggers, master_triggers)

    np.testing.assert_allclose(selected, events["time"])
    output = capsys.readouterr().out
    assert "accepting 1 long Input1 pulse(s)" in output
    assert "maximum absolute residual 4.63118 ms" in output


def test_sync_selection_rejects_long_pulse_and_warns_for_large_residual(capsys):
    events = pd.DataFrame(
        [
            {"time": 10.0, "code": "Trigger1", "duration": 0.0},
            {"time": 20.0, "code": "Trigger1", "duration": 0.0},
            {"time": 30.0, "code": "Input1", "duration": 1.0},
            {"time": 40.0, "code": "Trigger1", "duration": 0.0},
        ]
    )
    short_triggers = np.array([10.0, 20.0, 40.0])
    master_triggers = np.array([0.0, 10.0, 20.0, 30.1])

    selected = select_rwd_sync_triggers(events, short_triggers, master_triggers)

    np.testing.assert_allclose(selected, short_triggers)
    output = capsys.readouterr().out
    assert "WARNING: RWD sync recovery maximum residual" in output
    assert "exceeds 20 ms" in output
    assert "will not be used" in output


def test_automatic_rwd_marker_import_uses_current_marker_schema():
    params = SimpleNamespace(
        markers=pd.DataFrame(
            [
                {"marker_id": "start", "marker": "o", "linked": True},
                {"marker_id": "opto_on", "marker": "1", "linked": False},
                {"marker_id": "opto_off", "marker": "0", "linked": False},
            ]
        )
    )
    events = pd.DataFrame(
        [
            {"time": 1.0, "code": "Input3", "duration": 2.0},
            {"time": 5.0, "code": "Trigger2", "duration": 3.0},
        ]
    )
    measures = {}

    _import_rwd_markers(measures, events, np.array([0.0]), np.array([0.0]), params)

    markers = measures["markers"]
    assert [marker["marker"] for marker in markers] == ["1", "0", "o1"]
    assert [marker["marker_id"] for marker in markers] == [
        "opto_on",
        "opto_off",
        "start",
    ]
    assert [marker["duration"] for marker in markers] == pytest.approx([2.0, 0.0, 3.0])
    assert set(markers[0]["parameters"]) == {"frequency", "pulse_width", "power"}
    assert all(np.isnan(value) for value in markers[0]["parameters"].values())
    assert markers[2]["parameters"] == {"stimulus_id": 1}
    assert measures["measures_version"] == CURRENT_MEASURES_VERSION
