from types import SimpleNamespace

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from novitrack.check_markers import check_markers
from novitrack.compute_event_measures import compute_event_measures
from novitrack.get_ethogram import get_ethogram
from novitrack.get_events import get_events
from novitrack.plot_events import plot_events
from novitrack.show_markers import show_markers


def _params():
    return SimpleNamespace(
        markers=pd.DataFrame(
            [
                {"marker_id": "start", "marker": "o", "description": "start", "color": [0, 0, 1], "behavior": False, "linked": True},
                {"marker_id": "stop", "marker": "t", "description": "stop", "color": [1, 0, 0], "behavior": False, "linked": True},
                {"marker_id": "approach", "marker": "a", "description": "approach", "color": [0, 1, 0], "behavior": True, "linked": True},
                {"marker_id": "opto_on", "marker": "1", "description": "laser on", "color": [0, 0, 1], "behavior": False, "linked": False},
                {"marker_id": "opto_off", "marker": "0", "description": "laser off", "color": [0, 0, 0], "behavior": False, "linked": False},
            ]
        ),
        nt_stim_marker_ids=["start"],
        nt_stop_marker_id="stop",
        nt_pretime=1,
        nt_posttime=1,
        use_clean_baseline=False,
        use_ultraclean_baseline=False,
        show_markers=True,
        nt_show_behavior_markers=True,
    )


def _marker(time, marker_id, *, duration=np.nan, **parameters):
    return {
        "time": float(time),
        "marker": "legacy-field-is-ignored",
        "marker_id": marker_id,
        "duration": duration,
        "parameters": parameters,
    }


def test_get_events_uses_marker_ids_and_expands_parameters():
    events = get_events(
        {"markers": [_marker(1, "opto_on", frequency=20.0, pulse_width=0.01, power=0.002)]},
        _params(),
    )

    assert events.loc[0, "event"] == "opto_on"
    assert events.loc[0, "marker_id"] == "opto_on"
    assert events.loc[0, "parameters"] == {
        "frequency": 20.0,
        "pulse_width": 0.01,
        "power": 0.002,
    }
    assert events.loc[0, "frequency"] == 20.0


def test_marker_consistency_pairs_stimulus_ids_without_legacy_strings():
    record = {
        "sessionid": "test",
        "measures": {
            "markers": [
                _marker(1, "start", stimulus_id=2),
                _marker(2, "stop", duration=0, stimulus_id=2),
            ]
        },
    }
    assert check_markers(record, _params(), verbose=False)

    record["measures"]["markers"][1]["parameters"]["stimulus_id"] = 3
    assert not check_markers(record, _params(), verbose=False)


def test_event_measures_keep_aligned_event_metadata_at_marker_id_level():
    params = _params()
    measures = {
        "markers": [
            _marker(
                0.5,
                "opto_on",
                duration=1.0,
                frequency=5.0,
                pulse_width=0.01,
                unused=np.array([]),
            ),
            _marker(2, "approach"),
            _marker(
                3,
                "opto_on",
                duration=2.0,
                frequency=30.0,
                pulse_width=0.01,
                power=0.002,
                unused=np.array([]),
            ),
        ],
        "snippets_tbins": np.array([-0.5, 0.5]),
        "min_time": 0.0,
        "max_time": 6.0,
    }
    snippets = {"data": {"signal": np.arange(6, dtype=float).reshape(3, 2)}, "unit": {"signal": "zscore"}}

    out = compute_event_measures(snippets, measures, params)

    event = out["event"]["opto_on"]
    assert event["parameters"]["frequency"].tolist() == [5.0, 30.0]
    assert event["parameters"]["pulse_width"].tolist() == [0.01]
    assert event["parameters"]["unused"].shape == (1,)
    assert event["parameters"]["unused"][0].size == 0
    assert event["parameters"]["power"][1] == 0.002
    assert np.isnan(event["parameters"]["power"][0])
    assert event["duration"].tolist() == [1.0, 2.0]
    assert event["signal"]["event_mean"].shape == (2,)
    assert "parameters" not in event["signal"]
    assert "duration" not in event["signal"]

    figures = plot_events({"measures": out}, params, snippets)
    assert figures
    assert all(len(figure.axes) == 2 for figure in figures)
    for figure in figures:
        plt.close(figure)


def test_ethogram_uses_marker_id_and_allows_duration_events_to_overlap():
    record = {
        "sessionid": "test",
        "measures": {
            "markers": [
                _marker(0, "approach", duration=2.0),
                _marker(1, "other", duration=2.0),
            ],
            "min_time": 0.0,
            "max_time": 3.0,
        },
    }
    params = _params()
    params.markers = pd.concat(
        [
            params.markers,
            pd.DataFrame([{"marker_id": "other", "marker": "x", "description": "other", "color": [1, 0, 0], "behavior": True, "linked": False}]),
        ],
        ignore_index=True,
    )

    ethogram, time, _motifs, _ax = get_ethogram(record, show=False, params=params)
    overlap = (time >= 1.0) & (time < 2.0)
    assert np.all(ethogram[overlap, 0] > 0)
    assert np.all(ethogram[overlap, 1] > 0)


def test_show_markers_looks_up_color_by_marker_id():
    fig, ax = plt.subplots()
    ax.set_xlim(0, 2)
    ax.set_ylim(0, 1)
    show_markers([_marker(1, "approach")], ax, _params())
    assert ax.lines[0].get_color() == (0.0, 1.0, 0.0)
    plt.close(fig)
