"""PyQt6/PyQtGraph behavior tracking GUI for NoviTrack records."""

from __future__ import annotations

import sys
import time
from collections.abc import Callable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PyQt6.QtCore import QEventLoop, QLineF, QRectF, QSize, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QCloseEvent, QIcon, QKeyEvent
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

try:
    import pyqtgraph as pg
except ImportError as exc:  # pragma: no cover - dependency checked at runtime
    pg = None
    _PYQTGRAPH_IMPORT_ERROR = exc
else:
    _PYQTGRAPH_IMPORT_ERROR = None

from inpythotools.logmsg import logmsg
from .change_times import change_times
from .import_markers import IMPORT_OPTIONS, import_markers
from .load_parameters import load_parameters
from .load_tracking_data import load_tracking_data
from .marker_schema import make_marker_record
from .open_videos import OpenCVVideoReader, VideoInfo, movie_search_locations, open_videos


_OPEN_WINDOWS: list["NTTrackBehaviorWindow"] = []
_SPEEDS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 4.0, 8.0, 16.0]
_ICON_SIZE = QSize(24, 24)
_LUCIDE_ICON_DIR = Path(__file__).with_name("icons") / "lucide"
_TRACKER_ACTIONS = (
    ("previous_marker", "Previous marker", "skip-back", "Shift+P"),
    ("backward_frame", "Previous video frame", "step-back", "Left"),
    ("toggle_play", "Play / pause", "pause", "Space"),
    ("forward_frame", "Next video frame", "step-forward", "Right"),
    ("next_marker", "Next marker", "skip-forward", "Shift+N"),
    ("speed_decrease", "Decrease playback speed", "rewind", "-"),
    ("speed_original", "Reset playback speed to 1x", "refresh-cw", "="),
    ("speed_increase", "Increase playback speed", "fast-forward", "+"),
    ("add_marker_dialog", "Add marker", "map-pin-plus", "Shift+M"),
    ("import_markers_dialog", "Import markers", "file-input", "Shift+I"),
    ("delete_next_marker", "Delete next marker", "map-pin-minus", "Del"),
    ("delete_all_markers", "Delete all markers", "trash-2", "Shift+D"),
    ("toggle_behavior_markers", "Show / hide behavioral markers", "map-pin", "B"),
    ("goto_dialog", "Go to time", "clock-arrow-up", "Shift+G"),
    ("show_help", "Help", "circle-help", "Shift+H"),
    ("close", "Stop / close tracker", "square", "Shift+Q"),
)


@dataclass(frozen=True)
class _ObservableSpec:
    field: str
    y_range: tuple[float, float]


_OBSERVABLES: dict[str, _ObservableSpec] = {
    "Speed": _ObservableSpec("Speed", (-0.25, 0.25)),
    "Rotation": _ObservableSpec("Angular_velocity", (-360.0, 360.0)),
    "Distance": _ObservableSpec("Object_distance", (0.0, 300.0)),
    "Absolute rotation": _ObservableSpec("Abs_angular_velocity", (0.0, 360.0)),
    "Distance to center": _ObservableSpec("Distance_to_center", (0.0, 300.0)),
    "Heading": _ObservableSpec("alpha", (-180.0, 180.0)),
    "Total speed": _ObservableSpec("Speed", (0.0, 0.375)),
    "Forward speed": _ObservableSpec("Forward_speed", (-0.25, 0.25)),
    "X position": _ObservableSpec("CoM_X", (0.0, 1000.0)),
    "Y position": _ObservableSpec("CoM_Y", (0.0, 1000.0)),
}
_DEFAULT_OBSERVABLE_PANELS = ("Speed", "Rotation", "Distance")


def _lucide_icon(name: str) -> QIcon:
    """Load a bundled 24 px Lucide tracker icon."""
    return QIcon(str(_LUCIDE_ICON_DIR / f"{name}.svg"))


def _add_toolbar_action(
    window: QMainWindow,
    toolbar: QToolBar,
    *,
    text: str,
    icon_name: str,
    shortcut: str,
    slot: Callable[..., Any],
) -> QAction:
    """Create an icon-only toolbar action with accessible descriptive text."""
    action = QAction(_lucide_icon(icon_name), text, window)
    action.setShortcut(shortcut)
    action.setToolTip(text)
    action.triggered.connect(slot)
    toolbar.addAction(action)
    button = toolbar.widgetForAction(action)
    if button is not None:
        button.setAccessibleName(text)
    return action


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _set_record_field(record: Any, name: str, value: Any) -> None:
    if isinstance(record, MutableMapping):
        record[name] = value
    elif isinstance(record, pd.Series):
        record.at[name] = value
    else:
        setattr(record, name, value)


def _as_array(value: Any, default: Sequence[float] | None = None) -> np.ndarray:
    if value is None:
        return np.asarray(default if default is not None else [], dtype=float)
    try:
        return np.asarray(value, dtype=float).reshape(-1)
    except (TypeError, ValueError):
        return np.asarray(default if default is not None else [], dtype=float)


def _ensure_measures(record: Any, params: Any) -> dict[str, Any]:
    measures = _get(record, "measures", None)
    if not isinstance(measures, dict):
        measures = {}
    measures.pop("events", None)
    measures.setdefault("markers", [])
    measures.setdefault("object_positions", np.empty((0, 5)))
    if bool(_get(params, "neurotar", False)):
        measures.setdefault("overhead_neurotar_headring", _get(params, "overhead_neurotar_headring", [np.nan, np.nan]))
        measures.setdefault("overhead_neurotar_center", _get(params, "overhead_neurotar_center", [np.nan, np.nan]))
    else:
        measures.setdefault("overhead_arena_center", _get(params, "overhead_arena_center", [np.nan, np.nan]))
    _set_record_field(record, "measures", measures)
    return measures


def _markers_as_records(markers: Any) -> list[dict[str, Any]]:
    if markers is None:
        return []
    if isinstance(markers, pd.DataFrame):
        return markers.to_dict(orient="records")
    if isinstance(markers, Mapping):
        return [dict(markers)]
    records: list[dict[str, Any]] = []
    try:
        iterator = list(markers)
    except TypeError:
        return records
    for marker in iterator:
        if isinstance(marker, Mapping):
            records.append(dict(marker))
        else:
            records.append({"time": _get(marker, "time", np.nan), "marker": _get(marker, "marker", "")})
    return sorted(records, key=lambda item: float(item.get("time", np.nan)))


def _marker_definition(params: Any, marker_key: str) -> Mapping[str, Any] | None:
    table = _get(params, "markers", pd.DataFrame())
    if not isinstance(table, pd.DataFrame) or table.empty:
        return None
    hits = table[table["marker"].astype(str) == str(marker_key)[0]]
    if hits.empty:
        return None
    return hits.iloc[0].to_dict()


def _qt_color(value: Any) -> tuple[int, int, int]:
    arr = _as_array(value, [0.0, 0.0, 0.0])
    arr = np.clip(arr[:3], 0.0, 1.0)
    return tuple(int(round(v * 255)) for v in arr)


class _MarkerOverlay(pg.GraphicsObject if pg is not None else object):
    """Paint timeline markers as one viewport-aware graphics item.

    A separate ``InfiniteLine`` for every marker is expensive because each line
    participates in Qt's scene indexing and in every ViewBox range update.  This
    item keeps sorted NumPy arrays instead and only submits lines inside the
    currently exposed x range to the painter.
    """

    _Y_MIN = -1.0e9
    _Y_MAX = 1.0e9

    def __init__(
        self,
        plot: Any,
        times: Sequence[float],
        colors: Sequence[tuple[int, int, int]],
        behavior_flags: Sequence[bool] | None = None,
    ) -> None:
        super().__init__()
        self._plot = plot
        self.times = np.asarray(times, dtype=float)
        self._pens: list[Any] = []
        pen_indices = np.empty(self.times.size, dtype=np.int32)
        pen_lookup: dict[tuple[int, int, int], int] = {}
        for index, color in enumerate(colors):
            pen_index = pen_lookup.get(color)
            if pen_index is None:
                pen_index = len(self._pens)
                pen_lookup[color] = pen_index
                self._pens.append(pg.mkPen(color, width=1))
            pen_indices[index] = pen_index
        self._pen_indices = pen_indices
        if behavior_flags is None:
            behavior_flags = [False] * self.times.size
        self.behavior_flags = np.asarray(behavior_flags, dtype=bool)
        if self.behavior_flags.size != self.times.size:
            raise ValueError("behavior_flags must have one entry per marker time")
        self._nt_marker = True
        self.setZValue(100)

    def boundingRect(self) -> QRectF:
        if self.times.size == 0:
            return QRectF()
        x0 = float(self.times[0])
        x1 = float(self.times[-1])
        # A non-empty rectangle is needed when all markers share one time.
        width = max(x1 - x0, np.finfo(float).eps * max(1.0, abs(x0)))
        return QRectF(x0, self._Y_MIN, width, self._Y_MAX - self._Y_MIN)

    def visible_slice(self, x_range: Sequence[float]) -> slice:
        """Return the marker slice intersecting ``x_range`` in O(log n)."""
        if self.times.size == 0:
            return slice(0, 0)
        x0, x1 = sorted((float(x_range[0]), float(x_range[1])))
        return slice(
            int(np.searchsorted(self.times, x0, side="left")),
            int(np.searchsorted(self.times, x1, side="right")),
        )

    @staticmethod
    def vertical_range(y_range: Sequence[float], is_behavior: bool) -> tuple[float, float]:
        """Return the marker span, leaving a visible overlap band by marker type."""
        y0, y1 = sorted((float(y_range[0]), float(y_range[1])))
        height = y1 - y0
        if is_behavior:
            return y0 + 0.2 * height, y1
        return y0, y0 + 0.8 * height

    def paint(self, painter: Any, option: Any, widget: Any = None) -> None:
        del widget
        if self.times.size == 0:
            return
        view_box = self._plot.getViewBox()
        x_range, y_range = view_box.viewRange()
        exposed = option.exposedRect
        x0 = max(float(min(x_range)), float(exposed.left()))
        x1 = min(float(max(x_range)), float(exposed.right()))
        if x1 < x0:
            return
        visible = self.visible_slice((x0, x1))
        times = self.times[visible]
        if times.size == 0:
            return
        pen_indices = self._pen_indices[visible]
        behavior_flags = self.behavior_flags[visible]
        for pen_index, pen in enumerate(self._pens):
            for is_behavior in (False, True):
                pen_times = times[(pen_indices == pen_index) & (behavior_flags == is_behavior)]
                if pen_times.size == 0:
                    continue
                y0, y1 = self.vertical_range(y_range, is_behavior)
                painter.setPen(pen)
                painter.drawLines([QLineF(float(x), y0, float(x), y1) for x in pen_times])


def _orient_camera_frame(frame: np.ndarray) -> np.ndarray:
    """Return a frame in the orientation used by the tracking display."""
    return np.flipud(frame).copy()


def _orient_camera_y(y: np.ndarray, frame_height: int) -> np.ndarray:
    """Mirror original movie y coordinates to match the displayed frame."""
    return float(frame_height - 1) - y


def _record_title(record: Any) -> str:
    sessionid = _get(record, "sessionid", "unknown session")
    subject = _get(record, "subject", "")
    return f"{sessionid} {subject}".strip()


def _missing_movies_message(record: Any, params: Any) -> str:
    folder, locations = movie_search_locations(record, params)
    lines = [
        "No NoviTrack movies were found for this record.",
        "",
        f"Searched in: {folder}",
    ]
    if locations:
        lines.extend(("", f"Configured cameras: {', '.join(locations)}"))
    else:
        lines.extend(("", "No camera names are configured in nt_camera_names."))
    return "\n".join(lines)


def _ask_y_range(
    parent: QWidget,
    observable_name: str,
    current_range: tuple[float, float],
) -> tuple[float, float] | None:
    dialog = QDialog(parent)
    dialog.setWindowTitle(f"{observable_name} y-axis range")
    form = QFormLayout(dialog)
    minimum = QDoubleSpinBox(dialog)
    maximum = QDoubleSpinBox(dialog)
    for control, value in zip((minimum, maximum), current_range):
        control.setDecimals(6)
        control.setRange(-1.0e12, 1.0e12)
        control.setValue(float(value))
    form.addRow("Minimum:", minimum)
    form.addRow("Maximum:", maximum)
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
        parent=dialog,
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    form.addRow(buttons)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    y_range = (minimum.value(), maximum.value())
    if y_range[0] >= y_range[1]:
        QMessageBox.warning(parent, "Invalid range", "The minimum must be smaller than the maximum.")
        return None
    return y_range


class _ObservablePanel(QWidget):
    """One configurable time-course panel in the bottom tracker row."""

    def __init__(self, owner: "NTTrackBehaviorWindow", observable_name: str) -> None:
        super().__init__(owner)
        self.owner = owner
        self.observable_name = observable_name
        self.y_range = _OBSERVABLES[observable_name].y_range
        self.setMinimumWidth(80)
        self.setMaximumWidth(450)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = QWidget(self)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(6, 0, 2, 0)
        header_layout.setSpacing(2)
        self.title_label = QLabel(self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.title_label, 1)
        self.delete_button = QToolButton(self)
        self.delete_button.setText("×")
        self.delete_button.setToolTip("Delete this observable panel")
        self.delete_button.setAccessibleName("Delete observable panel")
        self.delete_button.clicked.connect(lambda: self.owner._delete_observable_panel(self))
        header_layout.addWidget(self.delete_button)
        layout.addWidget(header)

        self.plot = pg.PlotWidget()
        self.plot.setBackground("w")
        self.plot.setMenuEnabled(False)
        layout.addWidget(self.plot, 1)

        self.cursor = pg.InfiniteLine(0, angle=90, pen=pg.mkPen((230, 40, 40), width=2))
        self.cursor.setZValue(1000)
        self.plot.addItem(self.cursor)

        for widget in (self, header, self.title_label, self.plot):
            widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            widget.customContextMenuRequested.connect(
                lambda position, source=widget: self._show_context_menu(source.mapToGlobal(position))
            )
        self.set_observable(observable_name)

    def set_observable(self, observable_name: str) -> None:
        self.observable_name = observable_name
        self.y_range = _OBSERVABLES[observable_name].y_range
        self.title_label.setText(observable_name)
        self.plot.clear()
        self.plot.plot(
            self.owner.time_values,
            self.owner._observable_values(observable_name),
            pen=pg.mkPen("k"),
        )
        self.plot.setYRange(*self.y_range, padding=0)
        self.plot.addItem(self.cursor)
        self.owner._update_trace_ranges()
        self.owner._refresh_marker_items()
        self.owner._update_panel_controls()

    def set_y_range(self, y_range: tuple[float, float]) -> None:
        self.y_range = y_range
        self.plot.setYRange(*y_range, padding=0)

    def _show_context_menu(self, global_position: Any) -> None:
        menu = QMenu(self)
        observable_menu = menu.addMenu("Show observable")
        available = set(self.owner._available_observable_names())
        for name in _OBSERVABLES:
            action = observable_menu.addAction(name)
            action.setCheckable(True)
            action.setChecked(name == self.observable_name)
            action.setEnabled(name in available)
            action.triggered.connect(lambda checked=False, selected=name: self.set_observable(selected))
        menu.addSeparator()
        range_action = menu.addAction("Set y-axis range…")
        range_action.triggered.connect(self._change_y_range)
        reset_action = menu.addAction("Reset y-axis range")
        reset_action.triggered.connect(
            lambda: self.set_y_range(_OBSERVABLES[self.observable_name].y_range)
        )
        menu.exec(global_position)

    def _change_y_range(self) -> None:
        y_range = _ask_y_range(self, self.observable_name, self.y_range)
        if y_range is not None:
            self.set_y_range(y_range)


class NTTrackBehaviorWindow(QMainWindow):
    """First usable PyQt6 port of MATLAB ``track_behavior``."""

    tracking_closed = pyqtSignal()

    def __init__(
        self,
        record: Any,
        parent: QWidget | None = None,
        *,
        on_record_changed: Callable[[Any], None] | None = None,
    ) -> None:
        if pg is None:
            raise ImportError(
                "track_behavior needs pyqtgraph. Install it in the GUI environment, "
                "for example: conda install -n gui_pyqt -c conda-forge pyqtgraph"
            ) from _PYQTGRAPH_IMPORT_ERROR
        super().__init__(parent)

        pg.setConfigOptions(antialias=False, imageAxisOrder="row-major")
        self.record = record
        self._on_record_changed = on_record_changed
        self.params = load_parameters(record)
        self.measures = _ensure_measures(record, self.params)
        self.changed = False
        self.playing = True
        self.playback_speed = 1.0
        self.master_time = 0.0
        self._last_tick = time.perf_counter()
        self._fps_filtered = 0.0
        self._closed = False
        self._video_to_master: dict[int, tuple[float, float]] = {}
        self._master_to_video: dict[int, tuple[float, float]] = {}

        self.readers, self.video_info, self.active_cameras = open_videos(self.record, self.params)
        if not self.active_cameras:
            raise FileNotFoundError(_missing_movies_message(self.record, self.params))

        self.nt_data, trigger_times = load_tracking_data(
            self.record,
            self.params,
            recompute=False,
            video_info=self.video_info,
        )
        if not self.nt_data:
            raise FileNotFoundError("No Neurotar/tracking data were found for this record.")
        self.measures["trigger_times"] = _as_array(trigger_times, [0.0])

        self._prepare_time_alignment()
        self._prepare_tracking_arrays()
        self._build_ui()
        self._refresh_marker_items()
        self._seek(0.0, force=True)

        fps = max(1.0, min(float(self.video_info[self.active_cameras[0]].framerate), 60.0))
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self._tick)
        self.timer.start(max(1, int(round(1000 / fps))))

    def _prepare_time_alignment(self) -> None:
        trigger_times = _as_array(self.measures.get("trigger_times"), [0.0])
        if trigger_times.size == 0:
            trigger_times = np.array([0.0], dtype=float)
            self.measures["trigger_times"] = trigger_times
        max_time = 0.0
        min_time = 0.0
        for camera_index in self.active_cameras:
            info = self.video_info[camera_index]
            assert info is not None
            video_triggers = _as_array(info.trigger_times, [0.0])
            if video_triggers.size == 0:
                video_triggers = np.array([0.0], dtype=float)
            _, offset, multiplier = change_times(0.0, video_triggers, trigger_times)
            self._video_to_master[camera_index] = (offset, multiplier)
            _, offset, multiplier = change_times(0.0, trigger_times, video_triggers)
            self._master_to_video[camera_index] = (offset, multiplier)
            video_end, _, _ = change_times(info.duration, video_triggers, trigger_times)
            video_start, _, _ = change_times(0.0, video_triggers, trigger_times)
            max_time = max(max_time, float(np.asarray(video_end)))
            min_time = min(min_time, float(np.asarray(video_start)))

        time_values = _as_array(self.nt_data.get("Time"), [0.0])
        finite = time_values[np.isfinite(time_values)]
        if finite.size:
            min_time = min(min_time, float(np.nanmin(finite)))
            max_time = max(max_time, float(np.nanmax(finite)))
        self.min_time = min_time
        self.max_time = max_time
        self.measures["min_time"] = min_time
        self.measures["max_time"] = max_time

    def _prepare_tracking_arrays(self) -> None:
        self.time_values = _as_array(self.nt_data.get("Time"), [0.0])
        self.x_values = _as_array(self.nt_data.get("X"), np.full_like(self.time_values, np.nan))
        self.y_values = _as_array(self.nt_data.get("Y"), np.full_like(self.time_values, np.nan))
        self.alpha_values = _as_array(self.nt_data.get("alpha"), np.full_like(self.time_values, np.nan))
        self.com_x_values = _as_array(self.nt_data.get("CoM_X"), np.full_like(self.time_values, np.nan))
        self.com_y_values = _as_array(self.nt_data.get("CoM_Y"), np.full_like(self.time_values, np.nan))
        self.tail_x_values = _as_array(self.nt_data.get("tailbase_X"), np.full_like(self.time_values, np.nan))
        self.tail_y_values = _as_array(self.nt_data.get("tailbase_Y"), np.full_like(self.time_values, np.nan))
        self.speed_values = _as_array(
            self.nt_data.get("Forward_speed" if bool(_get(self.params, "nt_forward_speed_in_speed_trace", True)) else "Speed"),
            np.full_like(self.time_values, np.nan),
        )
        self.rotation_values = _as_array(self.nt_data.get("Angular_velocity"), np.full_like(self.time_values, np.nan))
        self.distance_values = _as_array(self.nt_data.get("Object_distance"), np.full_like(self.time_values, np.nan))

    def _observable_values(self, observable_name: str) -> np.ndarray:
        spec = _OBSERVABLES[observable_name]
        field = spec.field
        if observable_name == "Speed" and bool(_get(self.params, "nt_forward_speed_in_speed_trace", True)):
            field = "Forward_speed"
        return _as_array(self.nt_data.get(field), np.full_like(self.time_values, np.nan))

    def _available_observable_names(self) -> list[str]:
        return [
            name
            for name in _OBSERVABLES
            if self._observable_values(name).size == self.time_values.size
        ]

    def _initial_observable_names(self) -> list[str]:
        configured = _get(self.params, "nt_tracking_observable_panels", _DEFAULT_OBSERVABLE_PANELS)
        if isinstance(configured, str):
            configured = [configured]
        try:
            requested = [str(name) for name in configured]
        except TypeError:
            requested = list(_DEFAULT_OBSERVABLE_PANELS)
        available_names = self._available_observable_names()
        available = set(available_names)
        names = [name for name in requested if name in available]
        if not names:
            names = [available_names[0] if available_names else "Speed"]
        return names

    def _build_ui(self) -> None:
        self.setWindowTitle(f"Tracking - {_record_title(self.record)}")
        root = QWidget(self)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        self.setCentralWidget(root)

        toolbar = QToolBar("Tracking", self)
        toolbar.setIconSize(_ICON_SIZE)
        self.addToolBar(toolbar)
        self.toolbar_actions: dict[str, QAction] = {}
        for slot_name, text, icon_name, shortcut in _TRACKER_ACTIONS:
            if slot_name == "toggle_behavior_markers" and not bool(
                _get(self.params, "nt_show_behavior_markers", True)
            ):
                icon_name = "map-pin-off"
            self.toolbar_actions[slot_name] = _add_toolbar_action(
                self,
                toolbar,
                text=text,
                icon_name=icon_name,
                shortcut=shortcut,
                slot=getattr(self, slot_name),
            )

        status = QHBoxLayout()
        layout.addLayout(status)
        self.state_label = QLabel("Playing")
        self.time_label = QLabel("0.00")
        self.fps_label = QLabel("")
        self.speed_label = QLabel("1x")
        self.message_label = QLabel("Ready")
        self.message_label.setMinimumWidth(320)
        for label, widget in (
            ("State:", self.state_label),
            ("Time:", self.time_label),
            ("FPS:", self.fps_label),
            ("Speed:", self.speed_label),
        ):
            status.addWidget(QLabel(label))
            status.addWidget(widget)
        status.addWidget(QLabel("Status:"))
        status.addWidget(self.message_label, 1)
        status.addStretch(1)

        video_row = QHBoxLayout()
        layout.addLayout(video_row, stretch=5)
        self.video_views: dict[int, pg.PlotWidget] = {}
        self.video_images: dict[int, pg.ImageItem] = {}
        self.video_info_by_camera: dict[int, VideoInfo] = {}
        self.overhead_mouse_item: pg.PlotDataItem | None = None
        for camera_index in self.active_cameras:
            info = self.video_info[camera_index]
            assert info is not None
            plot = pg.PlotWidget(title=info.camera_name)
            plot.setAspectLocked(True)
            plot.setMouseEnabled(x=False, y=False)
            plot.getViewBox().setDefaultPadding(0)
            plot.hideAxis("left")
            plot.hideAxis("bottom")
            image = pg.ImageItem(axisOrder="row-major")
            plot.addItem(image)
            self.video_views[camera_index] = plot
            self.video_images[camera_index] = image
            self.video_info_by_camera[camera_index] = info
            video_row.addWidget(plot)

        overhead_index = int(_get(self.params, "nt_overhead_camera", 1)) - 1
        if overhead_index in self.video_views:
            self.overhead_mouse_item = pg.PlotDataItem(
                pen=pg.mkPen((0, 255, 0), width=2),
                symbol="o" if bool(_get(self.params, "nt_show_mouse_keypoints", True)) else None,
                symbolBrush=(0, 255, 0),
                symbolSize=5,
            )
            self.video_views[overhead_index].addItem(self.overhead_mouse_item)

        self.timeline = pg.PlotWidget()
        self.timeline.setBackground("w")
        self.timeline.setMouseEnabled(y=False)
        self.timeline.setYRange(0, float(_get(self.params, "nt_track_timeline_max_speed", 0.375)))
        self.timeline.setXRange(self.min_time, self.max_time, padding=0)
        self.timeline.plot(self.time_values, np.nan_to_num(np.abs(self.speed_values), nan=0.0), pen=pg.mkPen((140, 140, 140)))
        self.timeline_cursor = pg.InfiniteLine(
            self.master_time,
            angle=90,
            pen=pg.mkPen((230, 40, 40), width=3),
            movable=True,
        )
        self.timeline_cursor.setZValue(1000)
        self.timeline_cursor.sigPositionChangeFinished.connect(
            lambda item: self._jump_to_time(float(item.value()))
        )
        self.timeline.addItem(self.timeline_cursor)
        self.timeline.scene().sigMouseClicked.connect(self._timeline_clicked)
        layout.addWidget(self.timeline, stretch=1)

        self.trace_row = QHBoxLayout()
        self.trace_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(self.trace_row, stretch=2)
        self.trace_panels: list[_ObservablePanel] = []
        for observable_name in self._initial_observable_names():
            self._add_observable_panel(observable_name)
        self.add_panel_button = QToolButton(root)
        self.add_panel_button.setText("+")
        self.add_panel_button.setToolTip("Add an observable panel")
        self.add_panel_button.setAccessibleName("Add observable panel")
        self.add_panel_button.clicked.connect(self._add_next_observable_panel)
        self.trace_row.addWidget(self.add_panel_button, alignment=Qt.AlignmentFlag.AlignTop)
        self._update_panel_controls()

        self.resize(1200, 820)
        QTimer.singleShot(0, self._fit_video_views_to_height)

    def resizeEvent(self, event: Any) -> None:
        super().resizeEvent(event)
        QTimer.singleShot(0, self._fit_video_views_to_height)

    def _fit_video_views_to_height(self) -> None:
        """Fit the full movie frame with vertical size as the limiting scale."""
        for camera_index, plot in self.video_views.items():
            info = self.video_info_by_camera[camera_index]
            view_box = plot.getViewBox()
            rect = view_box.geometry()
            view_height = max(float(rect.height()), 1.0)
            view_width = max(float(rect.width()), 1.0)
            view_aspect = view_width / view_height

            x_center = info.width / 2.0
            x_span = max(float(info.width), float(info.height) * view_aspect)
            x0 = x_center - x_span / 2.0
            x1 = x_center + x_span / 2.0
            view_box.setRange(xRange=(x0, x1), yRange=(float(info.height), 0.0), padding=0)

    def _timeline_clicked(self, event: Any) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        view_box = self.timeline.getViewBox()
        if not view_box.sceneBoundingRect().contains(event.scenePos()):
            return
        position = view_box.mapSceneToView(event.scenePos())
        target_time = float(position.x())
        # Finish dispatching the mouse event before the potentially slow video
        # seek.  In particular, random access in H.264 files may synchronously
        # decode from an earlier keyframe.
        event.accept()
        QTimer.singleShot(0, lambda: self._complete_timeline_jump(target_time))

    def _complete_timeline_jump(self, target_time: float) -> None:
        self._jump_to_time(target_time)
        self._report_status(f"Jumped to {self.master_time:.2f} s")

    def _report_status(self, message: str) -> None:
        self.message_label.setText(message)

    def _record_changed(self) -> None:
        """Store tracker edits and notify an owning database browser."""
        self.changed = True
        _set_record_field(self.record, "measures", self.measures)
        callback = getattr(self, "_on_record_changed", None)
        if callback is not None:
            callback(self.record)

    def _add_observable_panel(self, observable_name: str) -> _ObservablePanel:
        panel = _ObservablePanel(self, observable_name)
        self.trace_panels.append(panel)
        add_button = getattr(self, "add_panel_button", None)
        if add_button is None:
            self.trace_row.addWidget(panel, stretch=1)
        else:
            self.trace_row.insertWidget(self.trace_row.indexOf(add_button), panel, stretch=1)
        self._update_panel_controls()
        self._refresh_marker_items()
        return panel

    def _add_next_observable_panel(self) -> None:
        used = {panel.observable_name for panel in self.trace_panels}
        observable_name = next(
            (name for name in self._available_observable_names() if name not in used),
            None,
        )
        if observable_name is not None:
            self._add_observable_panel(observable_name)
            self._report_status(f"Added {observable_name} panel")

    def _delete_observable_panel(self, panel: _ObservablePanel) -> None:
        if len(self.trace_panels) <= 1 or panel not in self.trace_panels:
            return
        observable_name = panel.observable_name
        self.trace_panels.remove(panel)
        self.trace_row.removeWidget(panel)
        panel.deleteLater()
        self._update_panel_controls()
        self._report_status(f"Deleted {observable_name} panel")

    def _update_panel_controls(self) -> None:
        panels = getattr(self, "trace_panels", [])
        can_delete = len(panels) > 1
        for panel in panels:
            panel.delete_button.setEnabled(can_delete)
        add_button = getattr(self, "add_panel_button", None)
        if add_button is not None:
            used = {panel.observable_name for panel in panels}
            add_button.setEnabled(any(name not in used for name in self._available_observable_names()))

    def _bottom_trace_plots(self) -> list[Any]:
        panels = getattr(self, "trace_panels", None)
        if panels is not None:
            return [panel.plot for panel in panels]
        # Compatibility for lightweight test doubles and callers created before
        # observable panels became dynamic.
        return [
            plot
            for name in ("speed_plot", "rotation_plot", "distance_plot")
            if (plot := getattr(self, name, None)) is not None
        ]

    def _refresh_marker_items(self) -> None:
        markers = _markers_as_records(self.measures.get("markers"))
        self.measures["markers"] = markers

        bottom_plots = NTTrackBehaviorWindow._bottom_trace_plots(self)
        timeline_plots = [self.timeline, *bottom_plots]
        for plot in timeline_plots:
            for item in list(plot.items()):
                if getattr(item, "_nt_marker", False):
                    plot.removeItem(item)

        if not bool(_get(self.params, "nt_show_markers", True)):
            return

        marker_plots = [self.timeline]
        if bool(_get(self.params, "nt_show_markers_in_bottom_panels", True)):
            marker_plots.extend(bottom_plots)

        marker_definitions: dict[str, Mapping[str, Any]] = {}
        marker_table = _get(self.params, "markers", pd.DataFrame())
        if isinstance(marker_table, pd.DataFrame) and "marker" in marker_table:
            marker_definitions = {
                str(row["marker"])[0]: row.to_dict()
                for _, row in marker_table.iterrows()
                if str(row["marker"])
            }
        marker_times: list[float] = []
        marker_colors: list[tuple[int, int, int]] = []
        marker_behavior_flags: list[bool] = []
        for marker in markers:
            marker_text = str(marker.get("marker", ""))
            marker_time = float(marker.get("time", np.nan))
            if not np.isfinite(marker_time):
                continue
            definition = marker_definitions.get(marker_text[:1])
            is_behavior = bool(definition.get("behavior", False)) if definition is not None else False
            if is_behavior and not bool(
                _get(self.params, "nt_show_behavior_markers", True)
            ):
                continue
            color = _qt_color(definition.get("color", [0, 0, 0]) if definition else [0, 0, 0])
            marker_times.append(marker_time)
            marker_colors.append(color)
            marker_behavior_flags.append(is_behavior)

        if not marker_times:
            return
        for plot in marker_plots:
            overlay = _MarkerOverlay(plot, marker_times, marker_colors, marker_behavior_flags)
            # Markers are decoration and must not influence auto-ranging.
            try:
                plot.addItem(overlay, ignoreBounds=True)
            except TypeError:  # Simple plot doubles used by unit tests.
                plot.addItem(overlay)

    def _tick(self) -> None:
        now = time.perf_counter()
        elapsed = now - self._last_tick
        self._last_tick = now
        if self.playing:
            self.master_time += elapsed * self.playback_speed
            if self.master_time > self.max_time:
                self.master_time = self.min_time
        self._seek(self.master_time)
        if elapsed > 0:
            fps = 1.0 / elapsed
            self._fps_filtered = fps if self._fps_filtered == 0 else 0.9 * self._fps_filtered + 0.1 * fps
            self.fps_label.setText(f"{self._fps_filtered:.0f}")

    def _seek(self, master_time: float, *, force: bool = False) -> None:
        self.master_time = max(self.min_time, min(float(master_time), self.max_time))
        camera_master_times = []
        for camera_index in self.active_cameras:
            reader = self.readers[camera_index]
            info = self.video_info[camera_index]
            if reader is None or info is None:
                continue
            offset, multiplier = self._master_to_video[camera_index]
            video_time = self.master_time * multiplier + offset
            if force or self.playing:
                frame = reader.read_at_time(video_time)
                if frame is not None:
                    frame = _orient_camera_frame(frame)
                    self.video_images[camera_index].setImage(frame, autoLevels=False)
            offset, multiplier = self._video_to_master[camera_index]
            camera_master_times.append(video_time * multiplier + offset)
        if camera_master_times:
            self.master_time = float(np.nanmean(camera_master_times))
        self._update_overlays()
        self._update_trace_ranges()
        self.time_label.setText(f"{self.master_time:.2f}")
        self.timeline_cursor.setValue(self.master_time)

    def _jump_to_time(self, master_time: float) -> None:
        """Seek without changing whether playback is running or paused."""
        was_playing = self.playing
        try:
            self._seek(master_time, force=True)
        finally:
            self._set_playing(was_playing)
            # Do not count time spent choosing or processing the jump as
            # playback time on the next timer tick.
            self._last_tick = time.perf_counter()

    def _current_index(self) -> int | None:
        if self.time_values.size == 0:
            return None
        index = int(np.searchsorted(self.time_values, self.master_time, side="right") - 1)
        if index < 0 or index >= self.time_values.size:
            return None
        return index

    def _update_overlays(self) -> None:
        if self.overhead_mouse_item is None or not bool(_get(self.params, "nt_show_overhead_mouse", True)):
            return
        index = self._current_index()
        if index is None:
            self.overhead_mouse_item.setData([], [])
            return
        x = np.asarray([self.x_values[index], self.com_x_values[index], self.tail_x_values[index]], dtype=float)
        y = np.asarray([self.y_values[index], self.com_y_values[index], self.tail_y_values[index]], dtype=float)
        overhead_index = int(_get(self.params, "nt_overhead_camera", 1)) - 1
        overhead_info = self.video_info[overhead_index]
        if overhead_info is not None:
            y = _orient_camera_y(y, overhead_info.height)
        finite = np.isfinite(x) & np.isfinite(y)
        if not np.any(finite):
            self.overhead_mouse_item.setData([], [])
            return
        self.overhead_mouse_item.setData(x[finite], y[finite])

    def _update_trace_ranges(self) -> None:
        half_window = float(_get(self.params, "nt_mouse_trace_window", 3.0))
        x0 = self.master_time - half_window
        x1 = self.master_time + half_window
        for panel in getattr(self, "trace_panels", []):
            panel.plot.setXRange(x0, x1, padding=0)
            panel.cursor.setValue(self.master_time)

    def toggle_play(self) -> None:
        self._set_playing(not self.playing)

        self._last_tick = time.perf_counter()
        self._report_status("Playing" if self.playing else "Paused")

    def _set_playing(self, playing: bool) -> None:
        """Set playback state and keep its label and toolbar icon in sync."""
        self.playing = playing
        action = getattr(self, "toolbar_actions", {}).get("toggle_play")
        if action is not None:
            action.setIcon(_lucide_icon("pause" if self.playing else "play"))
        self.state_label.setText("Playing" if self.playing else "Paused")

    def toggle_behavior_markers(self) -> None:
        visible = not bool(_get(self.params, "nt_show_behavior_markers", True))
        if isinstance(self.params, MutableMapping):
            self.params["nt_show_behavior_markers"] = visible
        else:
            setattr(self.params, "nt_show_behavior_markers", visible)
        action = getattr(self, "toolbar_actions", {}).get(
            "toggle_behavior_markers"
        )
        if action is not None:
            action.setIcon(_lucide_icon("map-pin" if visible else "map-pin-off"))
        self._refresh_marker_items()
        self._report_status(f"Behavior markers {'shown' if visible else 'hidden'}")

    def backward_frame(self) -> None:
        self._set_playing(False)
        self._seek(self.master_time - 1.0 / self._base_fps(), force=True)
        self._report_status(f"Stepped back to {self.master_time:.2f} s")

    def forward_frame(self) -> None:
        self._set_playing(False)
        self._seek(self.master_time + 1.0 / self._base_fps(), force=True)
        self._report_status(f"Stepped forward to {self.master_time:.2f} s")

    def _base_fps(self) -> float:
        info = self.video_info[self.active_cameras[0]]
        return float(info.framerate if info is not None else 30.0)

    def previous_marker(self) -> None:
        marker_times = [float(m["time"]) for m in _markers_as_records(self.measures.get("markers")) if float(m["time"]) < self.master_time - 0.04]
        if marker_times:
            self._jump_to_time(max(marker_times))
            self._report_status(f"Jumped to previous marker at {self.master_time:.2f} s")
        else:
            self._report_status("No previous marker")

    def next_marker(self) -> None:
        marker_times = [float(m["time"]) for m in _markers_as_records(self.measures.get("markers")) if float(m["time"]) > self.master_time + 0.04]
        if marker_times:
            self._jump_to_time(min(marker_times))
            self._report_status(f"Jumped to next marker at {self.master_time:.2f} s")
        else:
            self._report_status("No next marker")

    def goto_dialog(self) -> None:
        value, ok = QInputDialog.getDouble(self, "Go to", "Second:", self.master_time, self.min_time, self.max_time, 2)
        if ok:
            self._jump_to_time(value)
            self._report_status(f"Jumped to {self.master_time:.2f} s")

    def add_marker_dialog(self) -> None:
        definitions = _get(self.params, "markers", pd.DataFrame())
        marker_keys = {
            str(row["marker_id"]): str(row["marker"])
            for _, row in definitions.iterrows()
        }
        marker_id, ok = QInputDialog.getItem(
            self, "Add marker", "Marker:", list(marker_keys), 0, False
        )
        if ok and marker_id:
            self.add_marker(marker_keys[marker_id], marker_id=marker_id)

    def import_markers_dialog(self) -> None:
        was_playing = self.playing
        if was_playing:
            self._set_playing(False)
        try:
            self._run_import_markers_dialog()
        finally:
            if was_playing:
                self._set_playing(True)
                # Do not count time spent in modal import dialogs as playback.
                self._last_tick = time.perf_counter()

    def _run_import_markers_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Import Options")
        layout = QVBoxLayout(dialog)
        checkboxes = []
        for name in IMPORT_OPTIONS:
            checkbox = QCheckBox(name, dialog)
            checkbox.setChecked(True)
            layout.addWidget(checkbox)
            checkboxes.append(checkbox)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=dialog,
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self._report_status("Marker import cancelled")
            return

        selections = [name for name, checkbox in zip(IMPORT_OPTIONS, checkboxes) if checkbox.isChecked()]
        if not selections:
            self._report_status("No marker sources selected")
            return

        before = _markers_as_records(self.measures.get("markers"))

        def ask_stim_id(marker: str) -> int | None:
            value, ok = QInputDialog.getInt(
                self,
                "Stimulus",
                f"Stimulus id for marker {marker}:",
                1,
                1,
                9,
            )
            return value if ok else None

        def ask_trigger_shift() -> float | None:
            value, ok = QInputDialog.getDouble(
                self,
                "Trigger Time Shift",
                "Enter trigger time shift (in seconds):",
                0.0,
                -1e9,
                1e9,
                6,
            )
            return value if ok else None

        import_markers(
            self.record,
            selections,
            params=self.params,
            stim_id_provider=ask_stim_id,
            trigger_shift_provider=ask_trigger_shift,
        )
        self.measures = _ensure_measures(self.record, self.params)
        after = _markers_as_records(self.measures.get("markers"))
        self._refresh_marker_items()
        if after != before:
            self._record_changed()
            logmsg("Imported markers")
            self._report_status(f"Imported markers from {len(selections)} source(s)")
        else:
            self._report_status("No markers imported")

    def add_marker(self, marker_key: str, *, marker_id: str | None = None) -> None:
        definition = _marker_definition(self.params, marker_key)
        if definition is None:
            self._report_status(f"Unknown marker key {marker_key!r}")
            QMessageBox.warning(self, "Unknown marker", f"Marker {marker_key!r} is not in params.markers.")
            return
        marker_text = marker_key[0]
        if bool(definition.get("linked", False)):
            stim_id = 1 if bool(_get(self.params, "neurotar", False)) else 0
            if not bool(_get(self.params, "neurotar", False)):
                stim_id, ok = QInputDialog.getInt(self, "Stimulus", "Stimulus id:", 1, 1, 9)
                if not ok:
                    self._report_status("Marker insertion cancelled")
                    return
            marker_text = f"{marker_text}{stim_id}"

        markers = _markers_as_records(self.measures.get("markers"))
        if any(abs(float(m.get("time", np.nan)) - self.master_time) < 1e-9 and str(m.get("marker")) == marker_text for m in markers):
            logmsg(f"Marker {marker_text} already present at t = {self.master_time:g}.")
            self._report_status(f"Marker {marker_text} already present at {self.master_time:.2f} s")
            return
        markers.append(
            make_marker_record(
                self.master_time,
                marker_text,
                self.params,
                marker_id=marker_id,
            )
        )
        self.measures["markers"] = sorted(markers, key=lambda item: float(item["time"]))
        logmsg(f"Inserting marker '{marker_text}' at time {self.master_time:g}")
        if marker_key[0] == str(_get(self.params, "nt_stop_marker", "t")):
            positions = np.asarray(self.measures.get("object_positions", np.empty((0, 5))), dtype=float).reshape(-1, 5)
            stim_id = int(marker_text[1:]) if len(marker_text) > 1 and marker_text[1:].isdigit() else 1
            positions = np.vstack([positions, [self.master_time, np.nan, np.nan, float(_get(self.params, "ARENA", 1)), stim_id]])
            self.measures["object_positions"] = positions[np.argsort(positions[:, 0])]
        self._refresh_marker_items()
        self._record_changed()
        self._report_status(f"Added marker {marker_text} at {self.master_time:.2f} s")

    def delete_next_marker(self) -> None:
        markers = _markers_as_records(self.measures.get("markers"))
        later = [(i, marker) for i, marker in enumerate(markers) if float(marker.get("time", np.nan)) > self.master_time]
        if not later:
            self._report_status("No next marker to delete")
            return
        index, marker = later[0]
        answer = QMessageBox.question(self, "Delete marker", f"Delete marker {marker.get('marker')} at {float(marker.get('time')):.2f} s?")
        if answer != QMessageBox.StandardButton.Yes:
            self._report_status("Marker deletion cancelled")
            return
        logmsg(f"Deleting marker '{marker.get('marker')}' at time {float(marker.get('time')):g}")
        del markers[index]
        self.measures["markers"] = markers
        self._refresh_marker_items()
        self._record_changed()
        self._report_status(f"Deleted marker {marker.get('marker')} at {float(marker.get('time')):.2f} s")

    def delete_all_markers(self) -> None:
        answer = QMessageBox.question(
            self,
            "Delete all markers",
            "Do you want to delete all markers?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            self._report_status("Marker deletion cancelled")
            return

        logmsg("Deleting all markers")
        self.measures["markers"] = []
        self._refresh_marker_items()
        self._record_changed()
        self._report_status("Deleted all markers")

    def speed_increase(self) -> None:
        index = min(_SPEEDS.index(self.playback_speed) + 1, len(_SPEEDS) - 1)
        self.playback_speed = _SPEEDS[index]
        self.speed_label.setText(f"{self.playback_speed:g}x")
        self._report_status(f"Playback speed {self.playback_speed:g}x")

    def speed_decrease(self) -> None:
        index = max(_SPEEDS.index(self.playback_speed) - 1, 0)
        self.playback_speed = _SPEEDS[index]
        self.speed_label.setText(f"{self.playback_speed:g}x")
        self._report_status(f"Playback speed {self.playback_speed:g}x")

    def speed_original(self) -> None:
        self.playback_speed = 1.0
        self.speed_label.setText("1x")
        self._report_status("Playback speed 1x")

    def show_help(self) -> None:
        marker_lines = []
        table = _get(self.params, "markers", pd.DataFrame())
        if isinstance(table, pd.DataFrame):
            marker_lines = [f"{row.marker}: {row.description}" for row in table.itertuples()]
        QMessageBox.information(
            self,
            "Tracking help",
            "\n".join(
                [
                    "Space: play/pause",
                    "Left/Right: frame step",
                    "Shift+P/Shift+N: previous/next marker",
                    "+/-: playback speed",
                    "Shift+M: add marker",
                    "Shift+I: import markers",
                    "B: toggle behavior markers",
                    "Shift+G: go to time",
                    "Delete: delete next marker",
                    "Shift+D: delete all markers",
                    "Shift+H: show help",
                    "Shift+Q/Esc: stop tracking",
                    "",
                    *marker_lines,
                ]
            ),
        )

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        modifiers = event.modifiers()
        if key == Qt.Key.Key_M and modifiers == Qt.KeyboardModifier.ShiftModifier:
            self.add_marker_dialog()
        elif key == Qt.Key.Key_I and modifiers == Qt.KeyboardModifier.ShiftModifier:
            self.import_markers_dialog()
        elif key == Qt.Key.Key_Delete:
            self.delete_next_marker()
        elif key == Qt.Key.Key_D and modifiers == Qt.KeyboardModifier.ShiftModifier:
            self.delete_all_markers()
        elif key == Qt.Key.Key_B and modifiers == Qt.KeyboardModifier.NoModifier:
            self.toggle_behavior_markers()
        elif key == Qt.Key.Key_G and modifiers == Qt.KeyboardModifier.ShiftModifier:
            self.goto_dialog()
        elif key == Qt.Key.Key_Q and modifiers == Qt.KeyboardModifier.ShiftModifier:
            self.close()
        elif key == Qt.Key.Key_Escape:
            self.close()
        elif key == Qt.Key.Key_Left and modifiers == Qt.KeyboardModifier.AltModifier:
            self._seek(self.master_time - 5.0, force=True)
        elif key == Qt.Key.Key_Right and modifiers == Qt.KeyboardModifier.AltModifier:
            self._seek(self.master_time + 5.0, force=True)
        elif event.text():
            marker_key = event.text()
            if _marker_definition(self.params, marker_key) is not None:
                self.add_marker(marker_key)
            else:
                self._report_unmapped_key(event)
                super().keyPressEvent(event)
        else:
            self._report_unmapped_key(event)
            super().keyPressEvent(event)

    def _report_unmapped_key(self, event: QKeyEvent) -> None:
        text = event.text()
        key_name = text if text else f"key code {int(event.key())}"
        self._report_status(f"Unmapped key: {key_name}")

    def closeEvent(self, event: QCloseEvent) -> None:
        self._closed = True
        self.timer.stop()
        _set_record_field(self.record, "measures", self.measures)
        for reader in self.readers:
            if reader is not None:
                reader.close()
        if self in _OPEN_WINDOWS:
            _OPEN_WINDOWS.remove(self)
        super().closeEvent(event)
        self.tracking_closed.emit()


def track_behavior(
    record: Any,
    *,
    block: bool | None = None,
    parent: QWidget | None = None,
    on_record_changed: Callable[[Any], None] | None = None,
) -> Any:
    """Open the behavior tracking GUI for one NoviTrack record.

    If ``block`` is true, this function returns ``(record, changed)`` after the
    window closes. If ``block`` is false, it returns the live window object. The
    default is non-blocking when a QApplication already exists, which is friendlier
    inside Spyder, and blocking when this function creates the application.
    """
    app = QApplication.instance()
    created_app = app is None
    if app is None:
        app = QApplication(sys.argv)
    if block is None:
        block = created_app

    window = NTTrackBehaviorWindow(
        record,
        parent=parent,
        on_record_changed=on_record_changed,
    )
    if parent is not None:
        # The database action is waiting in a nested event loop.  Establishing
        # native ownership and modality prevents that originating window from
        # being activated above the tracker while a video seek is busy.
        window.setWindowFlag(Qt.WindowType.Window, True)
        window.setWindowModality(Qt.WindowModality.WindowModal)
    _OPEN_WINDOWS.append(window)
    window.show()
    window.raise_()
    window.activateWindow()

    if not block:
        return window

    loop = QEventLoop()
    window.tracking_closed.connect(loop.quit)
    if created_app:
        app.exec()
    else:
        loop.exec()
    return record, window.changed


def track_record(
    record: Any,
    *,
    parent: QWidget | None = None,
    on_record_changed: Callable[[Any], None] | None = None,
) -> Any:
    """Return an updated record only when tracking actually changed it."""
    updated_record, changed = track_behavior(
        record,
        block=True,
        parent=parent,
        on_record_changed=on_record_changed,
    )
    return updated_record if changed else None


__all__ = ["NTTrackBehaviorWindow", "track_behavior", "track_record"]


if __name__ == "__main__":
    from .mat_database import load_mat_database

    if len(sys.argv) < 2:
        raise SystemExit("Usage: python track_behavior.py database.mat [row_index]")
    db = load_mat_database(Path(sys.argv[1]))
    row = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    track_behavior(db.iloc[row], block=True)
