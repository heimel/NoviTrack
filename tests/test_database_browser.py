from types import SimpleNamespace

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
