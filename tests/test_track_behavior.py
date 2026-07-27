from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QMessageBox

from novitrack import track_behavior


def test_orient_camera_frame_flips_every_camera_top_to_bottom():
    frame = np.arange(2 * 3 * 3).reshape(2, 3, 3)
    expected = frame[::-1]

    oriented = track_behavior._orient_camera_frame(frame)

    np.testing.assert_array_equal(oriented, expected)
    assert oriented.flags.c_contiguous


def test_orient_camera_y_matches_vertically_flipped_frame():
    y = np.array([0.0, 1.0, 4.0])

    np.testing.assert_array_equal(
        track_behavior._orient_camera_y(y, frame_height=5),
        [4.0, 3.0, 0.0],
    )


def _window_stub(markers):
    measures = {"markers": markers}
    statuses = []
    refreshes = []
    changes = []
    window = SimpleNamespace(
        measures=measures,
        record={"measures": measures},
        changed=False,
        _on_record_changed=lambda record: changes.append(record),
        _refresh_marker_items=lambda: refreshes.append(True),
        _report_status=statuses.append,
    )
    window._record_changed = lambda: track_behavior.NTTrackBehaviorWindow._record_changed(window)
    return window, statuses, refreshes, changes


def test_delete_all_markers_clears_markers_after_confirmation(monkeypatch):
    window, statuses, refreshes, changes = _window_stub(
        [{"time": 1.0, "marker": "o"}, {"time": 2.0, "marker": "t"}]
    )
    monkeypatch.setattr(
        track_behavior.QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )

    track_behavior.NTTrackBehaviorWindow.delete_all_markers(window)

    assert window.measures["markers"] == []
    assert window.record["measures"] is window.measures
    assert window.changed is True
    assert refreshes == [True]
    assert changes == [window.record]
    assert statuses == ["Deleted all markers"]


def test_delete_all_markers_keeps_markers_when_cancelled(monkeypatch):
    markers = [{"time": 1.0, "marker": "o"}]
    window, statuses, refreshes, changes = _window_stub(markers)
    monkeypatch.setattr(
        track_behavior.QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.No,
    )

    track_behavior.NTTrackBehaviorWindow.delete_all_markers(window)

    assert window.measures["markers"] is markers
    assert window.changed is False
    assert refreshes == []
    assert changes == []
    assert statuses == ["Marker deletion cancelled"]


def test_record_changed_notifies_database_callback():
    window, _, _, changes = _window_stub([{"time": 1.0, "marker": "o"}])

    track_behavior.NTTrackBehaviorWindow._record_changed(window)

    assert window.changed is True
    assert window.record["measures"] is window.measures
    assert changes == [window.record]


def test_add_marker_logs_marker_and_time(monkeypatch):
    window, statuses, refreshes, changes = _window_stub([])
    window.params = SimpleNamespace(
        markers=pd.DataFrame([{"marker": "o", "linked": False}]),
        nt_stop_marker="t",
    )
    window.master_time = 12.5
    logs = []
    monkeypatch.setattr(track_behavior, "logmsg", logs.append)

    track_behavior.NTTrackBehaviorWindow.add_marker(window, "o")

    assert window.measures["markers"] == [{"time": 12.5, "marker": "o"}]
    assert logs == ["Inserting marker 'o' at time 12.5"]
    assert refreshes == [True]
    assert changes == [window.record]
    assert statuses == ["Added marker o at 12.50 s"]
