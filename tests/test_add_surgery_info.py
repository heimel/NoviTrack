from pathlib import Path

import novitrack.add_surgery_info as add_surgery_info_module
from novitrack.add_surgery_info import add_surgery_info


def test_missing_surgery_log_reports_exact_path(monkeypatch, tmp_path):
    session_folder = tmp_path / "subject" / "session"
    session_folder.mkdir(parents=True)
    messages = []
    monkeypatch.setattr(
        add_surgery_info_module,
        "session_path",
        lambda record, params: (session_folder, True),
    )
    monkeypatch.setattr(add_surgery_info_module, "logmsg", messages.append)

    add_surgery_info({"sessionid": "session", "measures": {}})

    expected = Path(tmp_path) / "Surgery" / "Surgery_sites.xlsx"
    assert messages == [f"Cannot find surgery log for session. Looked for {expected}"]
