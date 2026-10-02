from __future__ import annotations

import importlib
from types import SimpleNamespace

import numpy as np
import pytest

from novitrack.change_times import fit_clock_transform
from novitrack.tracking_stream import (
    TrackingStream,
    TrackingStreamCollection,
    tracking_stream_from_nt_data,
)


def _stream(*, stream_id="overhead_pose", camera_id="overhead") -> TrackingStream:
    transform = fit_clock_transform(
        [0.0, 2.0],
        [10.0, 12.0],
        source_clock="overhead_video",
        target_clock="reference",
    )
    return TrackingStream(
        stream_id=stream_id,
        source_type="test_pose",
        native_times=np.array([0.0, 1.0, 2.0]),
        data={
            "position": np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]),
            "confidence": np.array([0.8, 0.9, 1.0]),
            "description": "not sample-aligned",
        },
        clock_id="overhead_video",
        clock_transform=transform,
        coordinate_system="overhead_pixels",
        camera_id=camera_id,
        frame_indices=np.array([100, 101, 102]),
        capabilities=frozenset({"position", "pose_overlay"}),
    )


def test_tracking_stream_queries_native_data_in_reference_time() -> None:
    stream = _stream()

    np.testing.assert_allclose(stream.reference_times, [10.0, 11.0, 12.0])
    assert stream.start_reference_time == pytest.approx(10.0)
    assert stream.stop_reference_time == pytest.approx(12.0)

    sample = stream.sample_at(11.4)
    assert sample is not None
    assert sample.index == 1
    assert sample.native_time == 1.0
    assert sample.reference_time == pytest.approx(11.0)
    assert sample.frame_index == 101
    np.testing.assert_allclose(sample.values["position"], [3.0, 4.0])
    assert sample.values["confidence"] == 0.9
    assert "description" not in sample.values

    assert stream.sample_at(11.4, tolerance=0.3) is None
    assert stream.sample_for_frame(102).index == 2
    assert stream.sample_for_frame(999) is None


def test_tracking_stream_validates_clock_and_time_axes() -> None:
    transform = fit_clock_transform(
        [0.0, 1.0],
        [0.0, 1.0],
        source_clock="camera",
        target_clock="reference",
    )

    with pytest.raises(ValueError, match="start at clock_id"):
        TrackingStream(
            stream_id="bad-clock",
            source_type="test",
            native_times=[0.0, 1.0],
            data={},
            clock_id="another-camera",
            clock_transform=transform,
        )
    with pytest.raises(ValueError, match="must be ordered"):
        TrackingStream(
            stream_id="bad-times",
            source_type="test",
            native_times=[1.0, 0.0],
            data={},
        )


def test_tracking_stream_collection_selects_streams_and_bounds() -> None:
    overhead = _stream()
    side = _stream(stream_id="side_pose", camera_id="side")
    streams = TrackingStreamCollection([overhead, side])

    assert list(streams) == ["overhead_pose", "side_pose"]
    assert streams["overhead_pose"] is overhead
    assert streams.by_camera("overhead") == (overhead,)
    assert streams.with_capability("pose_overlay") == (overhead, side)
    assert streams.reference_bounds == pytest.approx((10.0, 12.0))

    with pytest.raises(ValueError, match="Duplicate"):
        streams.add(overhead)


def test_legacy_nt_data_adapter_preserves_fields_and_capabilities() -> None:
    nt_data = {
        "schema_version": 1,
        "Time": np.array([0.0, 0.5]),
        "Coordinates": 4,
        "X": np.array([1.0, 2.0]),
        "Y": np.array([3.0, 4.0]),
        "CoM_X": np.array([5.0, 6.0]),
        "CoM_Y": np.array([7.0, 8.0]),
        "alpha": np.array([90.0, 91.0]),
        "Speed": np.array([0.1, 0.2]),
    }

    stream = tracking_stream_from_nt_data(nt_data, camera_id=0)

    assert stream.reference_clock == "reference"
    assert stream.coordinate_system == 4
    assert stream.camera_id == 0
    assert stream.metadata["schema_version"] == 1
    assert {"position", "pose_overlay", "heading", "speed"} <= stream.capabilities
    assert "Time" not in stream.data
    np.testing.assert_allclose(stream.data["CoM_X"], [5.0, 6.0])


def test_stream_loader_wraps_legacy_loader_and_skips_empty_timelines(monkeypatch) -> None:
    module = importlib.import_module("novitrack.load_tracking_data")
    params = SimpleNamespace(neurotar=False, OVERHEAD=4, nt_overhead_camera=2)
    position_data = {
        "Time": np.array([0.0, 1.0]),
        "Coordinates": 4,
        "CoM_X": np.array([5.0, 6.0]),
        "CoM_Y": np.array([7.0, 8.0]),
    }
    monkeypatch.setattr(
        module,
        "load_tracking_data",
        lambda *args, **kwargs: (position_data, np.array([0.0, 5.0])),
    )

    streams, triggers = module.load_tracking_streams({}, params)

    assert list(streams) == ["legacy_tracking"]
    assert streams["legacy_tracking"].camera_id == 1
    np.testing.assert_allclose(triggers, [0.0, 5.0])

    empty_data = {
        "Time": np.array([0.0, 1.0]),
        "Coordinates": 4,
        "CoM_X": np.array([np.nan, np.nan]),
        "CoM_Y": np.array([np.nan, np.nan]),
    }
    monkeypatch.setattr(
        module,
        "load_tracking_data",
        lambda *args, **kwargs: (empty_data, np.array([])),
    )

    empty_streams, _ = module.load_tracking_streams({}, params)

    assert len(empty_streams) == 0
