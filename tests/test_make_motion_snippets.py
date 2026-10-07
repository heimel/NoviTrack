from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from novitrack.compute_event_measures import compute_event_measures
from novitrack.make_motion_snippets import make_motion_snippets


def _params(observables):
    return SimpleNamespace(
        nt_motion_snippet_observables=observables,
        nt_pretime=1.0,
        nt_posttime=1.0,
        nt_photometry_bin_width=0.5,
        use_clean_baseline=False,
        use_ultraclean_baseline=False,
        markers=[],
        nt_stop_marker_id="stop",
    )


def _measures():
    return {
        "markers": [
            {
                "time": 2.0,
                "marker": "s",
                "marker_id": "stimulus",
                "duration": 0.0,
                "parameters": {},
            }
        ],
        "snippets_tbins": np.array([-0.5, 0.0, 0.5]),
        "min_time": 0.0,
        "max_time": 4.0,
    }


def test_configured_motion_observables_feed_event_measures_with_units() -> None:
    params = _params(["Speed", "Forward_speed"])
    tracking = {
        "Time": np.arange(0.0, 4.5, 0.5),
        "Speed": np.arange(0.0, 4.5, 0.5),
        "Forward_speed": -np.arange(0.0, 4.5, 0.5),
        "Abs_angular_velocity": np.full(9, 20.0),
        "Units": {"Speed": "m/s", "Forward_speed": "m/s"},
    }

    snippets = make_motion_snippets(tracking, _measures(), None, params)
    event_measures = compute_event_measures(snippets, _measures(), params)

    assert set(snippets["data"]) == {"Speed", "Forward_speed"}
    np.testing.assert_allclose(snippets["data"]["Speed"], [[1.5, 2.0, 2.5]])
    np.testing.assert_allclose(snippets["data"]["Forward_speed"], [[-1.5, -2.0, -2.5]])
    assert snippets["unit"] == {"Speed": "m/s", "Forward_speed": "m/s"}
    assert set(event_measures["event"]["stimulus"]) == {
        "parameters",
        "duration",
        "Speed",
        "Forward_speed",
    }
    assert event_measures["event"]["stimulus"]["Speed"]["unit"] == "m/s"


def test_motion_snippets_do_not_bridge_long_missing_data_gaps() -> None:
    params = _params("Speed")
    tracking = {
        "Time": np.arange(0.0, 4.5, 0.5),
        "Speed": np.array([0.0, 0.5, 1.0, np.nan, np.nan, 2.5, 3.0, 3.5, 4.0]),
    }

    snippets = make_motion_snippets(tracking, _measures(), None, params)

    assert np.isnan(snippets["data"]["Speed"][0, :2]).all()
    assert snippets["data"]["Speed"][0, 2] == 2.5


def test_missing_or_misaligned_configured_observables_are_skipped() -> None:
    params = _params(["Speed", "not_a_trace", "Forward_speed"])
    tracking = {
        "Time": np.array([0.0, 1.0, 2.0, 3.0]),
        "Speed": np.array([0.0, 1.0, 2.0, 3.0]),
        "Forward_speed": np.array([1.0, 2.0]),
    }

    snippets = make_motion_snippets(tracking, _measures(), None, params)

    assert set(snippets["data"]) == {"Speed"}
