from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from novitrack.load_photometry import _import_rwd_markers, parse_channels
from novitrack.measures_schema import CURRENT_MEASURES_VERSION


@pytest.mark.parametrize("comment", [None, "", np.array([])])
def test_parse_channels_accepts_empty_comment_representations(comment):
    assert parse_channels(comment) == {}


def test_parse_channels_accepts_native_string():
    assert parse_channels("channel1 = signal, channel2 = isosbestic.") == {
        "Channel1": "signal",
        "Channel2": "isosbestic",
    }


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
