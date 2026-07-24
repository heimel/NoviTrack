from types import SimpleNamespace

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QMessageBox

from novitrack import track_behavior


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
