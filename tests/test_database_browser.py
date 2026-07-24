from types import SimpleNamespace

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
    monkeypatch.setattr(database_browser, "_install_filter_error_help", lambda window: None)
    monkeypatch.setattr(database_browser.QApplication, "instance", lambda: None)
    monkeypatch.setattr(database_browser, "_running_in_ipython", lambda: True)

    window = database_browser.experiment_db(filename="dummy.mat", block=None)

    assert window is not None
    assert captured["block"] is False
