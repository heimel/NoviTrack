import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtCore import QRect, QSize, Qt
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox, QToolBar

from novitrack import track_behavior
from novitrack.tracking_stream import TrackingStream, TrackingStreamCollection


def _tracking_stream(times, data=None, *, stream_id="tracking", capabilities=()):
    return TrackingStream(
        stream_id=stream_id,
        source_type="test",
        native_times=np.asarray(times, dtype=float),
        data={} if data is None else data,
        capabilities=frozenset(capabilities),
    )


def test_select_tracking_stream_prefers_position_data():
    heading = _tracking_stream(
        [0.0],
        {"alpha": [10.0]},
        stream_id="heading",
        capabilities={"heading"},
    )
    position = _tracking_stream(
        [0.0],
        {"X": [1.0], "Y": [2.0]},
        stream_id="position",
        capabilities={"position"},
    )

    selected = track_behavior._select_tracking_stream(
        TrackingStreamCollection([heading, position])
    )

    assert selected is position


def _dlc_prompt_window(*, position_available=False, processing=None):
    measures = {}
    if processing is not None:
        measures["tracking_processing"] = processing
    changes = []
    statuses = []
    window = SimpleNamespace(
        position_tracking_available=position_available,
        measures=measures,
        record={"subject": "0120360", "sessionid": "session-1", "measures": measures},
        params=SimpleNamespace(nt_overhead_camera=1),
        video_info=[],
        _record_changed=lambda: changes.append(True),
        _report_status=statuses.append,
    )
    window._set_tracking_processing_state = lambda response, state, **details: (
        track_behavior.NTTrackBehaviorWindow._set_tracking_processing_state(
            window, response, state=state, **details
        )
    )
    return window, changes, statuses


def test_dlc_prompt_is_skipped_when_tracking_exists_or_record_was_handled(monkeypatch):
    calls = []
    monkeypatch.setattr(
        track_behavior,
        "_ask_deeplabcut_queue_decision",
        lambda parent: calls.append(parent),
    )
    available, _, _ = _dlc_prompt_window(position_available=True)
    queued, _, _ = _dlc_prompt_window(
        processing={"method": "deeplabcut", "prompt_response": "queued"}
    )
    declined, _, _ = _dlc_prompt_window(
        processing={"method": "deeplabcut", "prompt_response": "never"}
    )

    for window in (available, queued, declined):
        track_behavior.NTTrackBehaviorWindow._maybe_offer_deeplabcut_processing(window)

    assert calls == []


def test_dlc_ask_later_decision_is_stored(monkeypatch):
    window, changes, _ = _dlc_prompt_window()
    monkeypatch.setattr(
        track_behavior,
        "_ask_deeplabcut_queue_decision",
        lambda parent: "ask_later",
    )

    track_behavior.NTTrackBehaviorWindow._maybe_offer_deeplabcut_processing(window)

    state = window.measures["tracking_processing"]
    assert state["method"] == "deeplabcut"
    assert state["prompt_response"] == "ask_later"
    assert state["state"] == "not_requested"
    assert changes == [True]


def test_dlc_queue_decision_selects_model_writes_job_and_stores_state(
    monkeypatch, tmp_path
):
    projects = tmp_path / "projects"
    project = projects / "overhead-mouse"
    project.mkdir(parents=True)
    config = project / "config.yaml"
    config.write_text("Task: overhead-mouse\n", encoding="utf-8")
    video = tmp_path / "session" / "session-1_overhead.mp4"
    video.parent.mkdir()
    video.write_bytes(b"video")
    window, changes, statuses = _dlc_prompt_window()
    window.params = SimpleNamespace(
        nt_overhead_camera=1,
        nt_deeplabcut_projects_folder=str(projects),
        nt_deeplabcut_queue_folder=str(tmp_path / "queue"),
    )
    window.video_info = [SimpleNamespace(filename=video, camera_name="overhead")]
    monkeypatch.setattr(
        track_behavior,
        "_ask_deeplabcut_queue_decision",
        lambda parent: "queue",
    )
    monkeypatch.setattr(
        track_behavior,
        "_choose_deeplabcut_project",
        lambda parent, choices: choices[0],
    )

    track_behavior.NTTrackBehaviorWindow._maybe_offer_deeplabcut_processing(window)

    manifests = list((tmp_path / "queue" / "pending").glob("*.json"))
    assert len(manifests) == 1
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    state = window.measures["tracking_processing"]
    assert manifest["video_path"] == str(video)
    assert manifest["dlc_config_path"] == str(config)
    assert state["prompt_response"] == "queued"
    assert state["state"] == "pending"
    assert state["job_id"] == manifest["job_id"]
    assert state["queue_manifest"] == str(manifests[0])
    assert changes == [True]
    assert statuses == ["Queued DeepLabCut analysis using overhead-mouse"]


def test_prepare_tracking_arrays_uses_stream_reference_time():
    stream = _tracking_stream(
        [0.0, 1.0],
        {"X": [3.0, 4.0], "Y": [5.0, 6.0], "Speed": [7.0, 8.0]},
    )
    window = SimpleNamespace(
        tracking_stream=stream,
        params=SimpleNamespace(),
    )

    track_behavior.NTTrackBehaviorWindow._prepare_tracking_arrays(window)

    np.testing.assert_array_equal(window.time_values, stream.reference_times)
    np.testing.assert_array_equal(window.x_values, [3.0, 4.0])
    np.testing.assert_array_equal(window.y_values, [5.0, 6.0])
    np.testing.assert_array_equal(window.speed_values, [7.0, 8.0])


def test_prepare_tracking_arrays_supports_video_only_session():
    window = SimpleNamespace(
        tracking_stream=None,
        params=SimpleNamespace(),
    )

    track_behavior.NTTrackBehaviorWindow._prepare_tracking_arrays(window)

    assert window.time_values.size == 0
    assert window.x_values.size == 0
    assert window.speed_values.size == 0


def test_raw_keypoint_stream_does_not_allocate_missing_legacy_traces():
    stream = _tracking_stream(
        np.arange(100_000, dtype=float),
        {
            "keypoints": np.zeros((100_000, 1, 2)),
            "likelihood": np.ones((100_000, 1)),
        },
        capabilities={"position", "pose_overlay"},
    )
    window = SimpleNamespace(
        tracking_stream=stream,
        position_tracking_available=True,
        params=SimpleNamespace(),
    )

    track_behavior.NTTrackBehaviorWindow._prepare_tracking_arrays(window)
    window._observable_values = lambda name: (
        track_behavior.NTTrackBehaviorWindow._observable_values(window, name)
    )
    names = track_behavior.NTTrackBehaviorWindow._available_observable_names(window)

    assert window.time_values.size == 100_000
    assert window.x_values.size == 0
    assert window.speed_values.size == 0
    assert names == []


def test_aligned_plot_data_skips_missing_or_misaligned_series():
    times, values = track_behavior._aligned_plot_data([0.0, 1.0], [])
    assert times.size == 0
    assert values.size == 0

    times, values = track_behavior._aligned_plot_data([0.0, 1.0], [2.0, 3.0])
    np.testing.assert_array_equal(times, [0.0, 1.0])
    np.testing.assert_array_equal(values, [2.0, 3.0])


def test_keypoint_colors_use_requested_colormap_and_fall_back_to_rainbow():
    colors = track_behavior._keypoint_colors("rainbow", 3)

    assert len(colors) == 3
    assert len(set(colors)) == 3
    assert all(len(color) == 4 for color in colors)
    assert track_behavior._keypoint_colors("not-a-colormap", 3) == colors


def test_current_index_uses_nearest_stream_sample():
    window = SimpleNamespace(
        tracking_stream=_tracking_stream([0.0, 1.0, 2.0]),
        master_time=1.8,
    )

    assert track_behavior.NTTrackBehaviorWindow._current_index(window) == 2


def test_current_index_is_none_without_tracking_stream():
    window = SimpleNamespace(tracking_stream=None, master_time=1.8)

    assert track_behavior.NTTrackBehaviorWindow._current_index(window) is None


def test_current_index_prefers_exact_source_video_frame():
    stream = TrackingStream(
        stream_id="pose",
        source_type="test",
        native_times=[0.0, 1.0, 2.0],
        data={},
        camera_id=1,
        frame_indices=[10, 20, 30],
    )
    window = SimpleNamespace(
        tracking_stream=stream,
        tracking_overlay_camera_index=1,
        _current_video_frames={1: 20},
        master_time=1.8,
    )

    assert track_behavior.NTTrackBehaviorWindow._current_index(window) == 1


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


def test_tracker_toolbar_starts_with_navigation_in_playback_order():
    assert [action[0] for action in track_behavior._TRACKER_ACTIONS[:5]] == [
        "previous_marker",
        "backward_frame",
        "toggle_play",
        "forward_frame",
        "next_marker",
    ]


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


def test_import_markers_temporarily_pauses_playback(monkeypatch):
    playback_states = []
    imported = []
    window = SimpleNamespace(
        playing=True,
        _last_tick=0.0,
        _run_import_markers_dialog=lambda: imported.append(True),
    )

    def set_playing(playing):
        playback_states.append(playing)
        window.playing = playing

    window._set_playing = set_playing
    monkeypatch.setattr(track_behavior.time, "perf_counter", lambda: 123.0)

    track_behavior.NTTrackBehaviorWindow.import_markers_dialog(window)

    assert imported == [True]
    assert playback_states == [False, True]
    assert window.playing is True
    assert window._last_tick == 123.0


def test_import_markers_leaves_paused_playback_paused():
    playback_states = []
    imported = []
    window = SimpleNamespace(
        playing=False,
        _set_playing=playback_states.append,
        _run_import_markers_dialog=lambda: imported.append(True),
    )

    track_behavior.NTTrackBehaviorWindow.import_markers_dialog(window)

    assert imported == [True]
    assert playback_states == []
    assert window.playing is False


@pytest.mark.parametrize("playing", [False, True])
def test_jump_to_time_restores_current_playback_state(monkeypatch, playing):
    playback_states = []
    seeks = []
    window = SimpleNamespace(playing=playing, _last_tick=0.0)

    def seek(value, *, force=False):
        seeks.append((value, force))
        # Verify that the jump helper restores state even if seeking changes it.
        window.playing = not playing

    def set_playing(value):
        playback_states.append(value)
        window.playing = value

    window._seek = seek
    window._set_playing = set_playing
    monkeypatch.setattr(track_behavior.time, "perf_counter", lambda: 123.0)

    track_behavior.NTTrackBehaviorWindow._jump_to_time(window, 42.5)

    assert seeks == [(42.5, True)]
    assert playback_states == [playing]
    assert window.playing is playing
    assert window._last_tick == 123.0


def test_timeline_click_is_accepted_before_slow_seek(monkeypatch):
    calls = []

    class FakeEvent:
        def button(self):
            return Qt.MouseButton.LeftButton

        def scenePos(self):
            return "scene-position"

        def accept(self):
            calls.append("accepted")

    view_box = SimpleNamespace(
        sceneBoundingRect=lambda: SimpleNamespace(contains=lambda position: True),
        mapSceneToView=lambda position: SimpleNamespace(x=lambda: 42.5),
    )
    window = SimpleNamespace(
        timeline=SimpleNamespace(getViewBox=lambda: view_box),
        _complete_timeline_jump=lambda value: calls.append(("jumped", value)),
    )
    monkeypatch.setattr(
        track_behavior.QTimer,
        "singleShot",
        lambda delay, callback: calls.append(("scheduled", delay)) or callback(),
    )

    track_behavior.NTTrackBehaviorWindow._timeline_clicked(window, FakeEvent())

    assert calls == ["accepted", ("scheduled", 0), ("jumped", 42.5)]


def test_owned_tracker_is_modal_and_activated_above_parent(monkeypatch):
    calls = []
    parent = object()

    class FakeWindow:
        def __init__(self, record, *, parent, on_record_changed):
            calls.append(("created", parent, on_record_changed))

        def setWindowFlag(self, flag, enabled):
            calls.append(("window-flag", flag, enabled))

        def setWindowModality(self, modality):
            calls.append(("modality", modality))

        def show(self):
            calls.append("shown")

        def raise_(self):
            calls.append("raised")

        def activateWindow(self):
            calls.append("activated")

    monkeypatch.setattr(track_behavior.QApplication, "instance", lambda: object())
    monkeypatch.setattr(track_behavior, "NTTrackBehaviorWindow", FakeWindow)

    window = track_behavior.track_behavior(
        {},
        block=False,
        parent=parent,
        on_record_changed=None,
    )

    assert calls == [
        ("created", parent, None),
        ("window-flag", Qt.WindowType.Window, True),
        ("modality", Qt.WindowModality.WindowModal),
        "shown",
        "raised",
        "activated",
    ]
    assert window is track_behavior._OPEN_WINDOWS.pop()


def test_tracker_fills_work_area_to_right_of_parent_on_secondary_monitor():
    screen = SimpleNamespace(availableGeometry=lambda: QRect(-1920, 0, 1920, 1080))
    parent = SimpleNamespace(
        screen=lambda: screen,
        frameGeometry=lambda: QRect(-1880, 40, 700, 800),
    )
    tracker = SimpleNamespace(
        geometry=lambda: QRect(-1000, 100, 600, 400),
        frameGeometry=lambda: QRect(-1008, 70, 616, 460),
        setGeometry=lambda *args: setattr(tracker, "geometry_call", args),
    )

    track_behavior._position_tracker_window(tracker, parent)

    assert tracker.geometry_call == (-1164, 30, 1156, 1020)


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


def test_dlc_overlay_filters_likelihood_and_draws_configured_skeleton():
    class FakeItem:
        def setData(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    stream = TrackingStream(
        stream_id="deeplabcut:overhead",
        source_type="deeplabcut",
        native_times=[0.0],
        data={
            "keypoints": np.array([[[10.0, 10.0], [20.0, 20.0], [30.0, 30.0]]]),
            "likelihood": np.array([[0.9, 0.8, 0.4]]),
        },
        camera_id=1,
        frame_indices=[5],
        metadata={
            "keypoint_names": ("nose", "body_center", "tail_base"),
            "skeleton": (("nose", "body_center"), ("body_center", "tail_base")),
            "likelihood_cutoff": 0.6,
        },
    )
    keypoints = FakeItem()
    skeleton = FakeItem()
    window = SimpleNamespace(
        tracking_stream=stream,
        tracking_keypoint_item=keypoints,
        tracking_skeleton_item=skeleton,
        tracking_keypoint_brushes=("nose", "body_center", "tail_base"),
        tracking_overlay_camera_index=1,
        _current_video_frames={1: 5},
        master_time=0.0,
        video_info=[None, SimpleNamespace(height=100)],
        params=SimpleNamespace(
            nt_show_mouse_keypoints=True,
            nt_show_mouse_skeleton=True,
        ),
    )
    window._current_index = lambda: (
        track_behavior.NTTrackBehaviorWindow._current_index(window)
    )

    track_behavior.NTTrackBehaviorWindow._update_keypoint_overlays(window)

    np.testing.assert_array_equal(keypoints.args[0], [10.0, 20.0])
    np.testing.assert_array_equal(keypoints.args[1], [89.0, 79.0])
    assert keypoints.kwargs["brush"] == ["nose", "body_center"]
    np.testing.assert_array_equal(skeleton.args[0][:-1], [10.0, 20.0])
    np.testing.assert_array_equal(skeleton.args[1][:-1], [89.0, 79.0])
    assert np.isnan(skeleton.args[0][-1])
    assert np.isnan(skeleton.args[1][-1])


def test_tracking_overlay_visibility_toggles_are_independent():
    updates = []
    statuses = []
    window = SimpleNamespace(
        params={
            "nt_show_mouse_keypoints": True,
            "nt_show_mouse_skeleton": True,
        },
        _update_overlays=lambda: updates.append(True),
        _report_status=statuses.append,
    )

    track_behavior.NTTrackBehaviorWindow.toggle_mouse_keypoints(window)
    track_behavior.NTTrackBehaviorWindow.toggle_mouse_skeleton(window)

    assert window.params["nt_show_mouse_keypoints"] is False
    assert window.params["nt_show_mouse_skeleton"] is False
    assert updates == [True, True]
    assert statuses == ["Tracking keypoints hidden", "Tracking skeleton hidden"]


@pytest.mark.parametrize(
    ("key", "method_name"),
    [
        (Qt.Key.Key_K, "toggle_mouse_keypoints"),
        (Qt.Key.Key_S, "toggle_mouse_skeleton"),
    ],
)
def test_tracking_overlay_shortcuts(key, method_name):
    calls = []
    event = SimpleNamespace(
        key=lambda: key,
        modifiers=lambda: Qt.KeyboardModifier.ShiftModifier,
        text=lambda: "",
    )
    window = SimpleNamespace(
        toggle_mouse_keypoints=lambda: calls.append("toggle_mouse_keypoints"),
        toggle_mouse_skeleton=lambda: calls.append("toggle_mouse_skeleton"),
    )

    track_behavior.NTTrackBehaviorWindow.keyPressEvent(window, event)

    assert calls == [method_name]


def test_bad_video_trigger_alignment_is_reported_and_excluded(monkeypatch, tmp_path):
    class FakeReader:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    good_reader = FakeReader()
    bad_reader = FakeReader()
    good_info = SimpleNamespace(
        camera_name="overhead",
        filename=tmp_path / "overhead.mp4",
        duration=20.0,
        framerate=30.0,
        trigger_times=np.array([1.0, 11.0]),
    )
    bad_info = SimpleNamespace(
        camera_name="side",
        filename=tmp_path / "side.mp4",
        duration=20.0,
        framerate=30.0,
        trigger_times=np.array([2.0, 2.001]),
    )
    window = SimpleNamespace(
        measures={"trigger_times": np.array([0.0, 10.0])},
        active_cameras=[0, 1],
        video_info=[good_info, bad_info],
        readers=[good_reader, bad_reader],
        tracking_stream=_tracking_stream([-0.5, 15.0]),
        _video_to_master={},
        _master_to_video={},
    )
    dialogs = []
    monkeypatch.setattr(
        track_behavior.QMessageBox,
        "critical",
        lambda parent, title, message: dialogs.append((parent, title, message)),
    )

    track_behavior.NTTrackBehaviorWindow._prepare_time_alignment(window)

    assert window.active_cameras == [0]
    assert good_reader.closed is False
    assert bad_reader.closed is True
    assert window.readers == [good_reader, None]
    assert window.min_time == pytest.approx(-1.0)
    assert window.max_time == pytest.approx(19.0)
    assert set(window._video_to_master) == {0}
    assert set(window._master_to_video) == {0}
    assert window._video_to_master is window._video_to_reference
    assert window._master_to_video is window._reference_to_video
    transform = window._video_to_reference[0]
    inverse = window._reference_to_video[0]
    np.testing.assert_allclose(inverse.apply(transform.apply([0.0, 10.0])), [0.0, 10.0])
    assert len(dialogs) == 1
    assert dialogs[0][0] is window
    assert dialogs[0][1] == "Video trigger alignment failed"
    assert "side" in dialogs[0][2]
    assert str(bad_info.filename) in dialogs[0][2]
    assert "10000" in dialogs[0][2]


def test_base_fps_falls_back_when_all_videos_are_rejected():
    window = SimpleNamespace(active_cameras=[], video_info=[])

    assert track_behavior.NTTrackBehaviorWindow._base_fps(window) == 30.0


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


def test_delete_next_marker_logs_same_line_as_matlab(monkeypatch):
    window, statuses, refreshes, changes = _window_stub(
        [{"time": 1.0, "marker": "o"}, {"time": 2.5, "marker": "t1"}]
    )
    window.master_time = 1.0
    messages = []
    monkeypatch.setattr(
        track_behavior.QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    monkeypatch.setattr(track_behavior, "logmsg", messages.append)

    track_behavior.NTTrackBehaviorWindow.delete_next_marker(window)

    assert messages == ["Deleting marker 't1' at time 2.5"]
    assert window.measures["markers"] == [{"time": 1.0, "marker": "o"}]
    assert refreshes == [True]
    assert changes == [window.record]
    assert statuses == ["Deleted marker t1 at 2.50 s"]


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
        markers=pd.DataFrame(
            [{"marker_id": "start", "marker": "o", "linked": False}]
        ),
        nt_stop_marker="t",
    )
    window.master_time = 12.5
    logs = []
    monkeypatch.setattr(track_behavior, "logmsg", logs.append)

    track_behavior.NTTrackBehaviorWindow.add_marker(window, "o")

    assert len(window.measures["markers"]) == 1
    marker = window.measures["markers"][0]
    assert marker["time"] == 12.5
    assert marker["marker"] == "o"
    assert marker["marker_id"] == "start"
    assert np.isnan(marker["duration"])
    assert marker["parameters"] == {}
    assert logs == ["Inserting marker 'o' at time 12.5"]
    assert refreshes == [True]
    assert changes == [window.record]
    assert statuses == ["Added marker o at 12.50 s"]


def test_add_marker_dialog_saves_selected_marker_id(monkeypatch):
    selections = []
    window = SimpleNamespace(
        params=SimpleNamespace(
            markers=pd.DataFrame(
                [{"marker_id": "escape", "marker": "e", "linked": False}]
            )
        ),
        add_marker=lambda marker, **kwargs: selections.append((marker, kwargs)),
    )
    monkeypatch.setattr(
        track_behavior.QInputDialog,
        "getItem",
        lambda *args: ("escape", True),
    )

    track_behavior.NTTrackBehaviorWindow.add_marker_dialog(window)

    assert selections == [("e", {"marker_id": "escape"})]


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
    monkeypatch.setattr(track_behavior.pg, "mkPen", lambda color, width: (color, width))

    track_behavior.NTTrackBehaviorWindow._refresh_marker_items(window)

    for plot in (window.timeline, window.speed_plot, window.rotation_plot, window.distance_plot):
        assert len(plot.items()) == 1
        assert plot.items()[0].times.tolist() == [1.0]
        assert plot.items()[0].behavior_flags.tolist() == [False]
        assert plot.items()[0]._nt_marker


def test_refresh_marker_items_classifies_stimulus_and_behavior_markers(monkeypatch):
    window = _marker_window(show_behavior=True)
    monkeypatch.setattr(track_behavior.pg, "mkPen", lambda color, width: (color, width))

    track_behavior.NTTrackBehaviorWindow._refresh_marker_items(window)

    overlay = window.timeline.items()[0]
    assert overlay.times.tolist() == [1.0, 2.0]
    assert overlay.behavior_flags.tolist() == [False, True]


def test_refresh_marker_items_can_disable_bottom_panel_markers(monkeypatch):
    window = _marker_window(show_bottom=False)
    monkeypatch.setattr(track_behavior.pg, "mkPen", lambda color, width: (color, width))

    track_behavior.NTTrackBehaviorWindow._refresh_marker_items(window)

    assert len(window.timeline.items()) == 1
    assert window.timeline.items()[0].times.tolist() == [1.0, 2.0]
    assert window.speed_plot.items() == []
    assert window.rotation_plot.items() == []
    assert window.distance_plot.items() == []


def test_marker_overlay_selects_only_markers_in_view(monkeypatch):
    monkeypatch.setattr(track_behavior.pg, "mkPen", lambda color, width: (color, width))
    times = np.arange(10_000, dtype=float)
    colors = [(0, 0, 0)] * len(times)

    overlay = track_behavior._MarkerOverlay(_FakePlot(), times, colors)
    visible = overlay.visible_slice((500.25, 505.75))

    assert overlay.times[visible].tolist() == [501.0, 502.0, 503.0, 504.0, 505.0]


def test_marker_overlay_uses_overlapping_vertical_spans():
    y_range = (-10.0, 90.0)

    stimulus_range = track_behavior._MarkerOverlay.vertical_range(y_range, False)
    behavior_range = track_behavior._MarkerOverlay.vertical_range(y_range, True)

    assert stimulus_range == pytest.approx((-10.0, 70.0))
    assert behavior_range == pytest.approx((10.0, 90.0))


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


def test_initial_observable_panels_follow_parameter_order_and_ignore_unknown_names():
    window = SimpleNamespace(
        params=SimpleNamespace(nt_tracking_observable_panels=["Distance", "unknown", "Speed"]),
        _available_observable_names=lambda: list(track_behavior._OBSERVABLES),
    )

    names = track_behavior.NTTrackBehaviorWindow._initial_observable_names(window)

    assert names == ["Distance", "Speed"]


def test_position_dependent_observables_are_unavailable_without_position_tracking():
    window = SimpleNamespace(
        position_tracking_available=False,
        time_values=np.arange(3, dtype=float),
        _observable_values=lambda name: np.arange(3, dtype=float),
    )

    names = track_behavior.NTTrackBehaviorWindow._available_observable_names(window)

    assert names == ["Speed", "Forward speed"]
    assert "Rotation" not in names
    assert "Distance" not in names


def test_observable_panel_uses_fixed_range_and_can_change_observable():
    app = QApplication.instance() or QApplication([])
    owner = QMainWindow()
    owner.time_values = np.array([0.0, 1.0, 2.0])
    owner._observable_values = lambda name: np.arange(3, dtype=float)
    owner._update_trace_ranges = lambda: None
    owner._refresh_marker_items = lambda: None
    owner._update_panel_controls = lambda: None
    owner._delete_observable_panel = lambda panel: None
    owner._available_observable_names = lambda: list(track_behavior._OBSERVABLES)

    panel = track_behavior._ObservablePanel(owner, "Speed")
    assert panel.observable_name == "Speed"
    assert panel.y_range == (0.0, 0.375)
    assert panel.maximumWidth() == 450

    panel.set_observable("Rotation")
    assert panel.observable_name == "Rotation"
    assert panel.y_range == (-360.0, 360.0)
    assert panel.title_label.text() == "Rotation"

    panel.set_y_range((-90.0, 90.0))
    assert panel.y_range == (-90.0, 90.0)
    panel.close()
    owner.close()
    app.processEvents()


def test_delete_panel_keeps_at_least_one_panel():
    statuses = []
    only_panel = SimpleNamespace(observable_name="Speed")
    window = SimpleNamespace(trace_panels=[only_panel], _report_status=statuses.append)

    track_behavior.NTTrackBehaviorWindow._delete_observable_panel(window, only_panel)

    assert window.trace_panels == [only_panel]
    assert statuses == []
