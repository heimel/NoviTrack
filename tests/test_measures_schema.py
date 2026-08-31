from pathlib import Path

import numpy as np
import pandas as pd
from inpythotools.mat_database import (
    load_mat_database as load_raw_mat_database,
    save_mat_database,
)

from novitrack.get_events import get_events
from novitrack.mat_database import load_mat_database
from novitrack.measures_schema import (
    CURRENT_MEASURES_VERSION,
    upgrade_database_measures,
)


def _legacy_database() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "sessionid": "session-1",
                "setup": "default",
                "condition": "",
                "stimulus": "",
                "measures": {
                    "markers": [
                        {"time": 2.0, "marker": "o2"},
                        {"time": 3.0, "marker": "1"},
                        {"time": 4.0, "marker": "0"},
                        {"time": 5.0, "marker": "x7"},
                    ]
                },
            }
        ]
    )


def test_upgrade_database_measures_adds_marker_schema_without_losing_legacy_fields():
    upgraded, report = upgrade_database_measures(_legacy_database())

    measures = upgraded.iloc[0]["measures"]
    assert measures["measures_version"] == CURRENT_MEASURES_VERSION
    assert report.records_upgraded == 1
    assert report.markers_upgraded == 4
    assert report.unknown_markers == (("session-1", 5.0, "x7"),)
    assert [marker["marker"] for marker in measures["markers"][:3]] == ["o2", "1", "0"]
    assert [marker["marker_id"] for marker in measures["markers"][:3]] == [
        "start",
        "opto_on",
        "opto_off",
    ]
    assert measures["markers"][0]["parameters"] == {"stimulus_id": 2}
    assert all(np.isnan(marker["duration"]) for marker in measures["markers"][:3])
    assert measures["markers"][3]["marker_id"] == "unknown"

    # Analyses use descriptive IDs and retain event-specific parameters.
    events = get_events(measures)
    assert events["event"].tolist() == ["start", "opto_on", "opto_off", "unknown"]
    assert events["marker_id"].tolist() == events["event"].tolist()
    assert events.loc[0, "parameters"] == {"stimulus_id": 2}
    assert events.loc[0, "stimulus_id"] == 2


def test_current_measures_version_takes_fast_path(monkeypatch):
    db = _legacy_database()
    db.at[0, "measures"]["measures_version"] = CURRENT_MEASURES_VERSION
    monkeypatch.setattr(
        "novitrack.measures_schema.load_parameters",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected")),
    )

    upgraded, report = upgrade_database_measures(db)

    assert upgraded is db
    assert not report.changed


def test_singleton_marker_mapping_is_converted_to_a_list():
    db = _legacy_database()
    db.at[0, "measures"]["markers"] = {"time": 2.0, "marker": "o12"}

    upgraded, _ = upgrade_database_measures(db)

    marker = upgraded.at[0, "measures"]["markers"][0]
    assert marker["time"] == 2.0
    assert marker["marker"] == "o12"
    assert marker["marker_id"] == "start"
    assert np.isnan(marker["duration"])
    assert marker["parameters"] == {"stimulus_id": 12}


def test_load_mat_database_backs_up_and_persists_one_time_upgrade(tmp_path: Path):
    filename = tmp_path / "nttestdb_example.mat"
    save_mat_database(_legacy_database(), filename)
    original_bytes = filename.read_bytes()

    loaded = load_mat_database(filename, save_upgraded=True)

    backups = list(tmp_path.glob("nttestdb_example_legacy_*.mat"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == original_bytes
    assert loaded.attrs["legacy_backup"] == backups[0]
    assert loaded.iloc[0]["measures"]["markers"][0]["marker_id"] == "start"

    persisted = load_raw_mat_database(filename)
    assert int(persisted.iloc[0]["measures"]["measures_version"]) == CURRENT_MEASURES_VERSION
    assert persisted.iloc[0]["measures"]["markers"][0]["marker"] == "o2"
    assert persisted.iloc[0]["measures"]["markers"][0]["marker_id"] == "start"
    assert persisted.iloc[0]["measures"]["markers"][0]["parameters"] == {
        "stimulus_id": 2
    }

    load_mat_database(filename)
    assert len(list(tmp_path.glob("nttestdb_example_legacy_*.mat"))) == 1


def test_default_load_upgrades_without_writing_or_backing_up(tmp_path: Path):
    filename = tmp_path / "source.mat"
    save_mat_database(_legacy_database(), filename)
    original_bytes = filename.read_bytes()

    loaded = load_mat_database(filename)

    assert loaded.iloc[0]["measures"]["measures_version"] == CURRENT_MEASURES_VERSION
    assert "legacy_backup" not in loaded.attrs
    assert filename.read_bytes() == original_bytes
    assert list(tmp_path.glob("source_legacy_*.mat")) == []
