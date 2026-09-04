from types import SimpleNamespace

import numpy as np
from scipy.io import loadmat, savemat

from novitrack.load_tracking_data import TRACKING_SCHEMA_VERSION, load_tracking_data


def _params(**overrides):
    values = {
        "nt_recompute_tracking_data": False,
        "nt_overhead_camera": 2,
        "nt_pose_temporal_filter_width": 1,
        "OVERHEAD": 4,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_constructs_and_saves_matlab_compatible_timeline(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "novitrack.load_tracking_data.load_neurotar_data", lambda record, params: ({}, None)
    )
    video_info = [
        SimpleNamespace(n_frames=99, framerate=10.0, trigger_times=np.array([1.0])),
        SimpleNamespace(n_frames=4, framerate=2.0, trigger_times=np.array([0.5, 1.5])),
    ]

    nt_data, trigger_times = load_tracking_data(
        {"measures": {}}, _params(), session_path=tmp_path, video_info=video_info
    )

    np.testing.assert_allclose(nt_data["Time"], [-0.5, 0.0, 0.5, 1.0])
    np.testing.assert_allclose(trigger_times, [0.0, 1.0])
    assert nt_data["schema_version"] == TRACKING_SCHEMA_VERSION
    assert np.isnan(nt_data["X"]).all()

    raw = loadmat(tmp_path / "nt_tracking_data.mat", struct_as_record=False, squeeze_me=True)
    assert raw["nt_data"].schema_version == TRACKING_SCHEMA_VERSION
    np.testing.assert_allclose(np.asarray(raw["nt_data"].Time).reshape(-1), nt_data["Time"])


def test_loads_legacy_mat_file_without_schema_version(monkeypatch, tmp_path):
    savemat(
        tmp_path / "nt_tracking_data.mat",
        {"nt_data": {"Time": np.array([0.0, 1.0]), "CoM_X": [2.0, 3.0], "CoM_Y": [4.0, 5.0]}},
    )
    monkeypatch.setattr(
        "novitrack.load_tracking_data.load_neurotar_data",
        lambda record, params: (_ for _ in ()).throw(AssertionError("cache should be used")),
    )

    nt_data, trigger_times = load_tracking_data(
        {"measures": {"trigger_times": [7.0]}}, _params(), session_path=tmp_path
    )

    np.testing.assert_allclose(nt_data["Time"], [0.0, 1.0])
    np.testing.assert_allclose(trigger_times, [7.0])
    assert "schema_version" not in nt_data


def test_cached_data_uses_video_triggers_when_record_has_none(tmp_path):
    savemat(tmp_path / "nt_tracking_data.mat", {"nt_data": {"Time": [0.0, 1.0]}})
    video_info = [
        SimpleNamespace(n_frames=2, framerate=1.0, trigger_times=np.array([4.0, 9.0]))
    ]

    _, trigger_times = load_tracking_data(
        {"measures": {}},
        _params(nt_overhead_camera=1),
        session_path=tmp_path,
        video_info=video_info,
    )

    np.testing.assert_allclose(trigger_times, [0.0, 5.0])


def test_can_construct_without_writing_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "novitrack.load_tracking_data.load_neurotar_data", lambda record, params: ({}, None)
    )
    video_info = [SimpleNamespace(n_frames=2, framerate=2.0, trigger_times=np.array([]))]

    nt_data, trigger_times = load_tracking_data(
        {},
        _params(nt_overhead_camera=1),
        session_path=tmp_path,
        video_info=video_info,
        save_cache=False,
    )

    np.testing.assert_allclose(nt_data["Time"], [0.0, 0.5])
    assert trigger_times.size == 0
    assert not (tmp_path / "nt_tracking_data.mat").exists()
