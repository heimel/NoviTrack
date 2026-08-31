from types import SimpleNamespace
import json

import pandas as pd
from PyQt6.QtCore import QPoint, QRect, QSize
from PyQt6.QtWidgets import QApplication

import novitrack.database_browser as database_browser
from inpythotools.database_browser import DatabaseBrowser


class _FakeScreen:
    def __init__(self, available):
        self._available = available

    def availableGeometry(self):
        return QRect(self._available)


class _FakeWindow:
    def __init__(self, frame, geometry=None, screen=None):
        self._frame = QRect(frame)
        self._geometry = QRect(geometry if geometry is not None else frame)
        self._screen = screen
        self.set_geometry_calls = []

    def screen(self):
        return self._screen

    def frameGeometry(self):
        return QRect(self._frame)

    def geometry(self):
        return QRect(self._geometry)

    def pos(self):
        return self._geometry.topLeft()

    def move(self, position):
        offset = position - self._geometry.topLeft()
        self._frame.translate(offset)
        self._geometry.translate(offset)

    def setGeometry(self, x, y, width, height):
        self.set_geometry_calls.append((x, y, width, height))
        left = self._geometry.left() - self._frame.left()
        top = self._geometry.top() - self._frame.top()
        right = self._frame.right() - self._geometry.right()
        bottom = self._frame.bottom() - self._geometry.bottom()
        self._geometry = QRect(x, y, width, height)
        self._frame = QRect(
            x - left,
            y - top,
            width + left + right,
            height + top + bottom,
        )


def test_import_button_uses_shared_24_px_icon():
    app = QApplication.instance() or QApplication([])
    window = DatabaseBrowser(pd.DataFrame())

    database_browser._install_import_button(window)

    button = window.import_button
    assert button.text() == ""
    assert button.accessibleName() == "Import records"
    assert button.iconSize() == QSize(24, 24)
    assert not button.icon().isNull()
    assert button.width() == button.height()

    window.close()
    app.processEvents()


def _navigation_states(window):
    return {
        button.accessibleName(): button.isEnabled()
        for button in window.findChildren(database_browser.QPushButton)
        if button.accessibleName() in database_browser._NAVIGATION_BUTTON_NAMES
    }


def test_navigation_buttons_follow_current_record_position():
    app = QApplication.instance() or QApplication([])
    window = DatabaseBrowser(pd.DataFrame({"sessionid": ["a", "b", "c"]}))
    database_browser._install_navigation_button_states(window)

    # The generic browser initially selects the last record.
    assert _navigation_states(window) == {
        "First record": True,
        "Previous record": True,
        "Next record": False,
        "Last record": False,
    }

    window.first_record()
    assert _navigation_states(window) == {
        "First record": False,
        "Previous record": False,
        "Next record": True,
        "Last record": True,
    }

    window.next_record()
    assert all(_navigation_states(window).values())

    window.close()
    app.processEvents()


def test_all_navigation_buttons_are_disabled_for_one_record():
    app = QApplication.instance() or QApplication([])
    window = DatabaseBrowser(pd.DataFrame({"sessionid": ["only"]}))
    database_browser._install_navigation_button_states(window)

    assert not any(_navigation_states(window).values())

    window.close()
    app.processEvents()


def test_result_figures_fill_space_right_of_browser():
    screen = _FakeScreen(QRect(20, 40, 1600, 900))
    browser = _FakeWindow(QRect(200, 150, 500, 650), screen=screen)
    figure_window_1 = _FakeWindow(
        QRect(0, 0, 650, 500),
        QRect(8, 30, 634, 462),
    )
    figure_window_2 = _FakeWindow(
        QRect(50, 50, 650, 500),
        QRect(58, 80, 634, 462),
    )
    figures = [
        SimpleNamespace(canvas=SimpleNamespace(manager=SimpleNamespace(window=window)))
        for window in (figure_window_1, figure_window_2)
    ]

    database_browser._layout_result_figures(browser, figures, gap=8)

    assert browser.frameGeometry().topLeft() == QPoint(20, 40)
    expected_frame = QRect(528, 40, 1092, 900)
    assert figure_window_1.frameGeometry() == expected_frame
    assert figure_window_2.frameGeometry() == expected_frame


def test_result_figure_layout_ignores_backends_without_qt_windows():
    screen = _FakeScreen(QRect(0, 0, 1200, 800))
    browser = _FakeWindow(QRect(0, 0, 400, 600), screen=screen)
    figure = SimpleNamespace(canvas=SimpleNamespace(manager=None))

    database_browser._layout_result_figures(browser, [figure])


def test_results_are_hidden_and_positioned_before_they_are_shown(monkeypatch):
    events = []
    figure = SimpleNamespace(
        show=lambda: events.append("show"),
        canvas=SimpleNamespace(
            draw_idle=lambda: events.append("draw"),
            flush_events=lambda: events.append("flush"),
        ),
    )

    def create_figures(record, *, show):
        assert show is False
        assert database_browser.plt.isinteractive() is False
        events.append("create")
        return [figure]

    monkeypatch.setattr(database_browser, "results_nttestrecord", create_figures)
    monkeypatch.setattr(database_browser, "_LAST_WINDOW", object())
    monkeypatch.setattr(
        database_browser,
        "_layout_result_figures",
        lambda browser, figures: events.append("layout"),
    )
    was_interactive = database_browser.plt.isinteractive()
    database_browser.plt.ion()
    try:
        result = database_browser.results_nttestrecord_from_gui(pd.Series())
        assert database_browser.plt.isinteractive() is True
    finally:
        database_browser.plt.interactive(was_interactive)

    assert result == [figure]
    assert events == ["create", "layout", "show", "draw", "flush"]


def test_filter_error_shows_syntax_help_without_traceback(monkeypatch):
    messages = []
    unexpected_errors = []
    window = SimpleNamespace(
        filter_box=SimpleNamespace(text=lambda: "subject = '123456'"),
        _show_error=lambda title, exc: unexpected_errors.append((title, exc)),
    )
    monkeypatch.setattr(
        database_browser.QMessageBox,
        "warning",
        lambda parent, title, message: messages.append((title, message)),
    )

    database_browser._install_filter_error_help(window)
    window._show_error("Filter failed", SyntaxError("invalid syntax"))

    assert not unexpected_errors
    assert len(messages) == 1
    assert messages[0][0] == "Invalid filter"
    assert "subject == '123456'" in messages[0][1]
    assert "equality uses == rather than =" in messages[0][1]
    assert "Traceback" not in messages[0][1]


def test_experiment_db_defaults_to_nonblocking_in_ipython(monkeypatch):
    captured = {}

    class FakeApp:
        def exec(self):
            raise AssertionError("experiment_db should avoid blocking in IPython")

    class FakeWindow:
        filter_box = SimpleNamespace(setPlaceholderText=lambda *_: None)
        destroyed = SimpleNamespace(connect=lambda *_: None)

    def fake_browse_database(*args, **kwargs):
        captured["block"] = kwargs["block"]
        captured["action_icons"] = kwargs["action_icons"]
        return FakeWindow()

    monkeypatch.setattr(database_browser, "_browse_database", fake_browse_database)
    monkeypatch.setattr(database_browser, "_load_gui_params", lambda yaml_file=None: (None, None))
    monkeypatch.setattr(database_browser, "load_mat_database", lambda filename: pd.DataFrame())
    monkeypatch.setattr(database_browser, "_install_import_button", lambda window: None)
    monkeypatch.setattr(database_browser, "_install_filter_error_help", lambda window: None)
    monkeypatch.setattr(database_browser.QApplication, "instance", lambda: None)
    monkeypatch.setattr(database_browser, "_running_in_ipython", lambda: True)

    window = database_browser.experiment_db(filename="dummy.mat", block=None)

    assert window is not None
    assert captured["block"] is False
    assert captured["action_icons"] == {
        "Analyze": "microscope",
        "Results": "chart-line",
        "Track": "route",
    }


def test_track_behavior_marks_open_database_dirty_on_marker_change(monkeypatch):
    record = pd.Series(
        {"sessionid": "session-1", "measures": {"markers": []}},
        name=7,
    )
    browser = SimpleNamespace(
        db=pd.DataFrame([record.to_dict()], index=[7]),
        dirty=False,
        refreshes=0,
        current_record_index=lambda: 7,
    )
    browser._set_dirty = lambda dirty: setattr(browser, "dirty", dirty)
    browser._refresh_view = lambda: setattr(browser, "refreshes", browser.refreshes + 1)
    monkeypatch.setattr(database_browser, "_LAST_WINDOW", browser)

    def fake_track_behavior(open_record, *, block, parent, on_record_changed):
        assert parent is browser
        open_record["measures"] = {
            "markers": [{"time": 2.0, "marker": "o"}],
        }
        on_record_changed(open_record)
        return open_record, True

    monkeypatch.setattr(
        "novitrack.track_behavior.track_behavior",
        fake_track_behavior,
    )

    result = database_browser.track_behavior_record(record)

    assert result is None
    assert browser.dirty is True
    assert browser.refreshes == 1
    assert browser.db.at[7, "measures"]["markers"] == [
        {"time": 2.0, "marker": "o"},
    ]


def test_insert_imported_records_after_current_and_skips_duplicates():
    db = pd.DataFrame(
        [
            {"sessionid": "one", "subject": "mouse-1"},
            {"sessionid": "two", "subject": "mouse-2"},
        ],
        index=[10, 20],
    )
    imported = pd.DataFrame(
        [
            {"sessionid": "one", "subject": "mouse-1"},
            {"sessionid": "new", "subject": "mouse-3"},
        ]
    )
    duplicate_questions = []

    merged, count = database_browser.insert_imported_records(
        db,
        imported,
        after_index=10,
        ask_import_duplicates=lambda: duplicate_questions.append(True) or False,
    )

    assert count == 1
    assert duplicate_questions == [True]
    assert merged["sessionid"].tolist() == ["one", "new", "two"]


def test_insert_imported_records_can_import_all_duplicates_after_one_question():
    db = pd.DataFrame(
        [{"sessionid": "same", "subject": "mouse-1", "comment": ""}]
    )
    imported = pd.DataFrame(
        [
            {"sessionid": "same", "subject": "mouse-1", "comment": "copy 1"},
            {"sessionid": "same", "subject": "mouse-1", "comment": "copy 2"},
        ]
    )
    question_count = 0

    def accept_duplicates():
        nonlocal question_count
        question_count += 1
        return True

    merged, count = database_browser.insert_imported_records(
        db,
        imported,
        after_index=0,
        ask_import_duplicates=accept_duplicates,
    )

    assert count == 2
    assert question_count == 1
    assert merged["comment"].iloc[1:].tolist() == ["copy 1", "copy 2"]


def test_collect_session_json_files_recurses_and_adds_database_fields(tmp_path):
    first_folder = tmp_path / "subject-a"
    second_folder = tmp_path / "subject-b" / "session"
    first_folder.mkdir()
    second_folder.mkdir(parents=True)
    (first_folder / "a_session.json").write_text(
        json.dumps({"sessionid": "a", "subject": "subject-a"}),
        encoding="utf-8",
    )
    (second_folder / "b_SESSION.JSON").write_text(
        json.dumps({"sessionid": "b", "subject": "subject-b"}),
        encoding="utf-8",
    )
    (second_folder / "unrelated.json").write_text(
        json.dumps({"sessionid": "ignored"}),
        encoding="utf-8",
    )

    imported = database_browser.collect_session_json_files(tmp_path)

    assert imported["sessionid"].tolist() == ["a", "b"]
    assert imported["datatype"].tolist() == ["", ""]
    assert imported["comment"].tolist() == ["", ""]
    assert imported["measures"].tolist() == [{}, {}]


def test_load_import_file_supports_json_record(tmp_path):
    filename = tmp_path / "example_session.json"
    filename.write_text(
        json.dumps({"sessionid": "example", "sessnr": 3}),
        encoding="utf-8",
    )

    imported = database_browser.load_import_file(filename)

    assert imported.to_dict(orient="records") == [
        {"sessionid": "example", "sessnr": 3}
    ]
