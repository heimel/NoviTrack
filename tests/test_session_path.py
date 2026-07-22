import importlib
from types import SimpleNamespace


session_path_module = importlib.import_module("novitrack.session_path")


def test_missing_networkpathbase_logs_local_config_instructions(monkeypatch, tmp_path):
    logs = []
    monkeypatch.setattr(session_path_module, "logmsg", logs.append)
    params = SimpleNamespace(networkpathbase=tmp_path / "missing-root")
    record = {
        "project": "project",
        "dataset": "dataset",
        "subject": "subject",
        "sessionid": "session",
    }

    folder, exists = session_path_module.session_path(record, params)

    assert not exists
    assert folder == tmp_path / "missing-root" / "project" / "Data_collection" / "dataset" / "subject" / "session"
    assert len(logs) == 1
    assert "networkpathbase" in logs[0]
    assert "processparams_local.py" in logs[0]
    assert "edit_local_config()" in logs[0]
