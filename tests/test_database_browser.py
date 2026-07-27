from types import SimpleNamespace
import json

import pandas as pd

import novitrack.database_browser as database_browser


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

    def fake_track_behavior(open_record, *, block, on_record_changed):
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
