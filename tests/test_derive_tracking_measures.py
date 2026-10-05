from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from novitrack.derive_tracking_measures import derive_pose_measures
from novitrack.tracking_stream import TrackingStream


def _stream(times, names, keypoints, likelihood=None):
    keypoints = np.asarray(keypoints, dtype=float)
    if likelihood is None:
        likelihood = np.ones(keypoints.shape[:2])
    return TrackingStream(
        stream_id="pose",
        source_type="deeplabcut",
        native_times=np.asarray(times, dtype=float),
        data={
            "keypoints": keypoints.copy(),
            "keypoints_arena": keypoints,
            "likelihood": np.asarray(likelihood, dtype=float),
        },
        coordinate_system="video_pixels",
        capabilities={"position", "pose_overlay", "arena_position"},
        metadata={"keypoint_names": tuple(names), "likelihood_cutoff": 0.6},
    )


def _params(**overrides):
    values = {
        "nt_tracking_interpolation_max_gap": 0.0,
        "nt_tracking_smoothing_window": 0.0,
        "nt_tracking_smoothing_polynomial_order": 2,
        "nt_tracking_position_keypoint": "body_center",
        "nt_tracking_body_direction_tail_keypoint": "tail_base",
        "nt_tracking_body_direction_head_keypoint": "neck",
        "nt_tracking_head_direction_origin_keypoint": "head_center",
        "nt_tracking_head_direction_tip_keypoint": "nose",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_computes_linear_and_direction_measures_in_agreed_units() -> None:
    names = ["nose", "head_center", "neck", "body_center", "tail_base"]
    frames = []
    for x in (0.0, 1.0, 2.0):
        frames.append(
            [
                [x + 1.0, 1.0],  # nose: head direction is up
                [x + 1.0, 0.0],
                [x + 0.5, 0.0],
                [x, 0.0],
                [x - 0.5, 0.0],
            ]
        )
    stream = derive_pose_measures(_stream([0, 1, 2], names, frames), _params())

    np.testing.assert_allclose(stream.data["position_arena"], [[0, 0], [1, 0], [2, 0]])
    np.testing.assert_allclose(stream.data["Speed"], 1.0)
    np.testing.assert_allclose(stream.data["Forward_speed"], 1.0)
    np.testing.assert_allclose(stream.data["body_direction"], 0.0)
    np.testing.assert_allclose(stream.data["head_direction"], 90.0)
    np.testing.assert_allclose(stream.data["movement_direction"], 0.0)
    np.testing.assert_allclose(stream.data["head_body_angle"], 90.0)
    np.testing.assert_allclose(stream.data["Angular_velocity"], 0.0)
    np.testing.assert_allclose(stream.data["Distance_to_center"], [0, 1, 2])
    assert np.shares_memory(stream.data["CoM_X"], stream.data["position_arena"])
    assert stream.metadata["derived_measures"]["units"]["Speed"] == "m/s"
    assert stream.metadata["derived_measures"]["units"]["body_angular_velocity"] == "deg/s"
    assert {"speed", "forward_speed", "body_direction", "head_direction"} <= stream.capabilities


def test_body_angular_velocity_is_counter_clockwise_positive_and_wrap_safe() -> None:
    names = ["body_center", "tail_base", "neck"]
    angles = np.radians([170.0, -180.0, -170.0])
    frames = []
    for angle in angles:
        frames.append(
            [
                [0.0, 0.0],
                [0.0, 0.0],
                [np.cos(angle), np.sin(angle)],
            ]
        )

    stream = derive_pose_measures(_stream([0, 1, 2], names, frames), _params())

    np.testing.assert_allclose(stream.data["body_direction"], [170, -180, -170])
    np.testing.assert_allclose(stream.data["Angular_velocity"], 10.0, atol=1e-12)


def test_interpolates_only_short_confidence_gaps_before_differentiating() -> None:
    names = ["body_center"]
    points = np.array([[[0.0, 0.0]], [[0.1, 0.0]], [[0.2, 0.0]], [[0.3, 0.0]]])
    likelihood = np.array([[1.0], [0.1], [1.0], [1.0]])
    stream = _stream([0.0, 0.1, 0.2, 0.3], names, points, likelihood)

    interpolated = derive_pose_measures(
        stream,
        _params(nt_tracking_interpolation_max_gap=0.21),
    )
    not_interpolated = derive_pose_measures(
        stream,
        _params(nt_tracking_interpolation_max_gap=0.19),
    )

    np.testing.assert_allclose(interpolated.data["position_arena"][:, 0], [0, 0.1, 0.2, 0.3])
    np.testing.assert_allclose(interpolated.data["Speed"], 1.0)
    assert np.isnan(not_interpolated.data["position_arena"][1]).all()
    assert np.isnan(not_interpolated.data["Speed"][:2]).all()
    np.testing.assert_allclose(not_interpolated.data["Speed"][2:], 1.0)


def test_older_nose_and_tail_base_tracking_uses_midpoint_position_and_body_axis() -> None:
    names = ["nose", "tail_base"]
    points = np.array(
        [
            [[1.0, 0.0], [-1.0, 0.0]],
            [[2.0, 0.0], [0.0, 0.0]],
            [[3.0, 0.0], [1.0, 0.0]],
        ]
    )

    stream = derive_pose_measures(_stream([0, 1, 2], names, points), _params())

    np.testing.assert_allclose(stream.data["position_arena"][:, 0], [0, 1, 2])
    np.testing.assert_allclose(stream.data["body_direction"], 0.0)
    np.testing.assert_allclose(stream.data["Forward_speed"], 1.0)
    assert stream.metadata["derived_measures"]["position_definition"] == "midpoint(nose,tail_base)"
    assert stream.metadata["derived_measures"]["body_direction_definition"] == "tail_base->nose"
    assert np.isnan(stream.data["head_direction"]).all()


def test_com_only_tracking_computes_position_and_speed_without_orientation() -> None:
    points = np.array([[[0.0, 0.0]], [[0.0, 1.0]], [[0.0, 2.0]]])

    stream = derive_pose_measures(_stream([0, 1, 2], ["com"], points), _params())

    np.testing.assert_allclose(stream.data["Speed"], 1.0)
    np.testing.assert_allclose(stream.data["movement_direction"], 90.0)
    assert np.isnan(stream.data["body_direction"]).all()
    assert np.isnan(stream.data["Forward_speed"]).all()
    assert "body_direction" not in stream.capabilities
    assert "forward_speed" not in stream.capabilities


def test_raw_pixel_stream_records_that_derived_measures_were_skipped() -> None:
    raw = TrackingStream(
        stream_id="raw",
        source_type="deeplabcut",
        native_times=[0.0],
        data={"keypoints": np.array([[[1.0, 2.0]]])},
        metadata={"keypoint_names": ("nose",)},
    )

    stream = derive_pose_measures(raw, _params())

    assert "Speed" not in stream.data
    assert stream.metadata["derived_measures"] == {
        "status": "skipped",
        "reason": "calibrated_keypoints_unavailable",
    }
