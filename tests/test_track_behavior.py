from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox, QToolBar

from novitrack import track_behavior


def test_tracker_toolbar_uses_selected_24_px_lucide_icons():
    app = QApplication.instance() or QApplication([])
    window = QMainWindow()
    toolbar = QToolBar(window)
    toolbar.setIconSize(track_behavior._ICON_SIZE)

    for _slot_name, text, icon_name, shortcut in track_behavior._TRACKER_ACTIONS:
        action = track_behavior._add_toolbar_action(
            window,
            toolbar,
            text=text,
            icon_name=icon_name,
            shortcut=shortcut,
            slot=lambda: None,
        )
        button = toolbar.widgetForAction(action)
        assert action.text() == text
        assert action.toolTip() == text
        assert not action.icon().isNull()
        assert button.accessibleName() == text

    assert toolbar.iconSize() == QSize(24, 24)
    assert not track_behavior._lucide_icon("play").isNull()
    assert not track_behavior._lucide_icon("map-pin-off").isNull()

    window.close()
    app.processEvents()


def test_playback_and_marker_visibility_icons_follow_state(monkeypatch):
    icon_names = []
    monkeypatch.setattr(
        track_behavior,
        "_lucide_icon",
        lambda name: icon_names.append(name) or name,
    )
    play_icons = []
    marker_icons = []
    state_labels = []
    refreshes = []
    statuses = []
    window = SimpleNamespace(
        playing=True,
        params=SimpleNamespace(nt_show_behavior_markers=True),
        toolbar_actions={
            "toggle_play": SimpleNamespace(setIcon=play_icons.append),
            "toggle_behavior_markers": SimpleNamespace(setIcon=marker_icons.append),
        },
        state_label=SimpleNamespace(setText=state_labels.append),
        _refresh_marker_items=lambda: refreshes.append(True),
        _report_status=statuses.append,
    )
    window._set_playing = lambda playing: (
        track_behavior.NTTrackBehaviorWindow._set_playing(window, playing)
    )

    track_behavior.NTTrackBehaviorWindow.toggle_play(window)
    track_behavior.NTTrackBehaviorWindow.toggle_behavior_markers(window)

    assert window.playing is False
    assert play_icons == ["play"]
    assert marker_icons == ["map-pin-off"]
    assert state_labels == ["Paused"]
    assert refreshes == [True]
    assert statuses == ["Paused", "Behavior markers hidden"]
    assert icon_names == ["play", "map-pin-off"]


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


class _FakeMarkerLine:
    def __init__(self, position, *, angle, pen):
        self.position = position
        self.angle = angle
        self.pen = pen
        self.z_value = None

    def setZValue(self, value):
        self.z_value = value


class _FakePlot:
    def __init__(self):
        self._items = []

    def items(self):
        return list(self._items)

    def addItem(self, item):
        self._items.append(item)

    def removeItem(self, item):
        self._items.remove(item)


def _marker_window(*, show_bottom=True, show_behavior=True):
    markers = [
        {"time": 1.0, "marker": "o"},
        {"time": 2.0, "marker": "a"},
    ]
    marker_table = pd.DataFrame(
        [
            {"marker": "o", "color": [0.0, 0.0, 1.0], "behavior": False},
            {"marker": "a", "color": [0.0, 0.7, 0.0], "behavior": True},
        ]
    )
    return SimpleNamespace(
        measures={"markers": markers},
        params=SimpleNamespace(
            markers=marker_table,
            nt_show_markers=True,
            nt_show_markers_in_bottom_panels=show_bottom,
            nt_show_behavior_markers=show_behavior,
        ),
        timeline=_FakePlot(),
        speed_plot=_FakePlot(),
        rotation_plot=_FakePlot(),
        distance_plot=_FakePlot(),
    )


def test_refresh_marker_items_adds_visible_markers_to_all_time_course_panels(monkeypatch):
    window = _marker_window(show_behavior=False)
    monkeypatch.setattr(track_behavior.pg, "InfiniteLine", _FakeMarkerLine)
    monkeypatch.setattr(track_behavior.pg, "mkPen", lambda color, width: (color, width))

    track_behavior.NTTrackBehaviorWindow._refresh_marker_items(window)

    for plot in (window.timeline, window.speed_plot, window.rotation_plot, window.distance_plot):
        assert [line.position for line in plot.items()] == [1.0]
        assert all(line._nt_marker for line in plot.items())


def test_refresh_marker_items_can_disable_bottom_panel_markers(monkeypatch):
    window = _marker_window(show_bottom=False)
    monkeypatch.setattr(track_behavior.pg, "InfiniteLine", _FakeMarkerLine)
    monkeypatch.setattr(track_behavior.pg, "mkPen", lambda color, width: (color, width))

    track_behavior.NTTrackBehaviorWindow._refresh_marker_items(window)

    assert [line.position for line in window.timeline.items()] == [1.0, 2.0]
    assert window.speed_plot.items() == []
    assert window.rotation_plot.items() == []
    assert window.distance_plot.items() == []


def test_toggle_behavior_markers_refreshes_marker_items():
    refreshes = []
    statuses = []
    window = SimpleNamespace(
        params=SimpleNamespace(nt_show_behavior_markers=True),
        _refresh_marker_items=lambda: refreshes.append(True),
        _report_status=statuses.append,
    )

    track_behavior.NTTrackBehaviorWindow.toggle_behavior_markers(window)

    assert window.params.nt_show_behavior_markers is False
    assert refreshes == [True]
    assert statuses == ["Behavior markers hidden"]
