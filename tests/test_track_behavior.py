from types import SimpleNamespace

import numpy as np
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
    return SimpleNamespace(
        measures=measures,
        record={"measures": measures},
        changed=False,
        _refresh_marker_items=lambda: refreshes.append(True),
        _report_status=statuses.append,
    ), statuses, refreshes


def test_delete_all_markers_clears_markers_after_confirmation(monkeypatch):
    window, statuses, refreshes = _window_stub(
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
    assert statuses == ["Deleted all markers"]


def test_delete_all_markers_keeps_markers_when_cancelled(monkeypatch):
    markers = [{"time": 1.0, "marker": "o"}]
    window, statuses, refreshes = _window_stub(markers)
    monkeypatch.setattr(
        track_behavior.QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.No,
    )

    track_behavior.NTTrackBehaviorWindow.delete_all_markers(window)

    assert window.measures["markers"] is markers
    assert window.changed is False
    assert refreshes == []
    assert statuses == ["Marker deletion cancelled"]
