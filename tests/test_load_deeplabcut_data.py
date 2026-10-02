from __future__ import annotations

import os
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from novitrack.load_deeplabcut_data import (
    discover_deeplabcut_sources,
    load_deeplabcut_stream,
)


def _video(tmp_path, *, camera_index=1, camera_name="overhead"):
    filename = tmp_path / f"session_{camera_name}.mp4"
    filename.touch()
    return SimpleNamespace(
        camera_index=camera_index,
        camera_name=camera_name,
        filename=filename,
        framerate=10.0,
        trigger_times=np.array([2.0, 12.0]),
    )


def _dlc_table():
    scorer = "DLC_model"
    columns = pd.MultiIndex.from_product(
        [[scorer], ["nose", "body_center", "tail_base"], ["x", "y", "likelihood"]]
    )
    values = np.array(
        [
            [1.0, 2.0, 0.91, 3.0, 4.0, 0.92, 5.0, 6.0, 0.93],
            [11.0, 12.0, 0.81, 13.0, 14.0, 0.82, 15.0, 16.0, 0.83],
        ]
    )
    return pd.DataFrame(values, index=[20, 21], columns=columns)


def test_discovers_newest_dlc_result_for_each_video(tmp_path):
    overhead = _video(tmp_path)
    side = _video(tmp_path, camera_index=2, camera_name="side")
    older = tmp_path / "session_overheadDLC_old.csv"
    newer = tmp_path / "session_overheadDLC_new.h5"
    unrelated = tmp_path / "different_movieDLC_result.csv"
    older.touch()
    newer.touch()
    unrelated.touch()
    os.utime(older, ns=(1_000_000_000, 1_000_000_000))
    os.utime(newer, ns=(2_000_000_000, 2_000_000_000))

    sources = discover_deeplabcut_sources([overhead, side])

    assert len(sources) == 1
    assert sources[0].filename == newer
    assert sources[0].camera_id == 1
    assert sources[0].camera_name == "overhead"


@pytest.mark.parametrize("extension", [".csv", ".h5"])
def test_loads_dlc_keypoints_likelihoods_frames_and_reference_times(tmp_path, extension):
    video = _video(tmp_path)
    filename = tmp_path / f"session_overheadDLC_model{extension}"
    table = _dlc_table()
    if extension == ".csv":
        table.to_csv(filename)
    else:
        table.to_hdf(filename, key="df_with_missing")
    source = discover_deeplabcut_sources([video])[0]

    stream = load_deeplabcut_stream(source, [0.0, 10.0])

    assert stream.stream_id == "deeplabcut:overhead"
    assert stream.source_type == "deeplabcut"
    assert stream.camera_id == 1
    assert stream.coordinate_system == "video_pixels"
    assert stream.metadata["keypoint_names"] == ("nose", "body_center", "tail_base")
    assert stream.metadata["scorers"] == ("DLC_model",)
    assert stream.metadata["frame_index_source"] == "table_index"
    assert stream.capabilities == frozenset({"position", "pose_overlay", "confidence"})
    np.testing.assert_array_equal(stream.frame_indices, [20, 21])
    np.testing.assert_allclose(stream.native_times, [2.0, 2.1])
    np.testing.assert_allclose(stream.reference_times, [0.0, 0.1], atol=1e-12)
    np.testing.assert_allclose(
        stream.data["keypoints"][1],
        [[11.0, 12.0], [13.0, 14.0], [15.0, 16.0]],
    )
    np.testing.assert_allclose(stream.data["likelihood"][0], [0.91, 0.92, 0.93])
    assert stream.sample_for_frame(21).index == 1


def test_uses_row_numbers_when_dlc_index_is_not_numeric(tmp_path):
    video = _video(tmp_path)
    filename = tmp_path / "session_overheadDLC_model.csv"
    table = _dlc_table()
    table.index = ["frame-a", "frame-b"]
    table.to_csv(filename)
    source = discover_deeplabcut_sources([video])[0]

    stream = load_deeplabcut_stream(source, [0.0, 10.0])

    np.testing.assert_array_equal(stream.frame_indices, [0, 1])
    np.testing.assert_array_equal(stream.data["source_index"], ["frame-a", "frame-b"])
    assert stream.metadata["frame_index_source"] == "row_number"


def test_loads_camera_specific_skeleton_configuration(tmp_path):
    video = _video(tmp_path)
    filename = tmp_path / "session_overheadDLC_model.h5"
    _dlc_table().to_hdf(filename, key="df_with_missing")
    config_folder = tmp_path / "DeepLabCut" / "overhead"
    config_folder.mkdir(parents=True)
    config = config_folder / "config.yaml"
    config.write_text(
        "pcutoff: 0.75\n"
        "dotsize: 7\n"
        "colormap: plasma\n"
        "skeleton_color: red\n"
        "skeleton:\n"
        "  - [nose, body_center]\n"
        "  - [body_center, tail_base]\n",
        encoding="utf-8",
    )

    source = discover_deeplabcut_sources([video])[0]
    stream = load_deeplabcut_stream(source, [0.0, 10.0])

    assert source.config_filename == config
    assert stream.metadata["config_file"] == str(config)
    assert stream.metadata["likelihood_cutoff"] == pytest.approx(0.75)
    assert stream.metadata["keypoint_size"] == pytest.approx(7.0)
    assert stream.metadata["keypoint_colormap"] == "plasma"
    assert stream.metadata["skeleton_color"] == "red"
    assert stream.metadata["skeleton"] == (
        ("nose", "body_center"),
        ("body_center", "tail_base"),
    )
