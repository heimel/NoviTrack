"""Common in-memory representation of independently timed tracking streams."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

import numpy as np

from .change_times import ClockTransform


def _readonly_vector(value: Any, *, dtype: Any = float) -> np.ndarray:
    vector = np.asarray(value, dtype=dtype).reshape(-1).copy()
    vector.setflags(write=False)
    return vector


def _finite_vector(value: Any) -> np.ndarray:
    try:
        return np.asarray(value, dtype=float).reshape(-1)
    except (TypeError, ValueError):
        return np.array([], dtype=float)


def _has_finite_pair(data: Mapping[str, Any], x_name: str, y_name: str) -> bool:
    x = _finite_vector(data.get(x_name, []))
    y = _finite_vector(data.get(y_name, []))
    return bool(x.size and x.size == y.size and np.any(np.isfinite(x) & np.isfinite(y)))


def _has_finite_values(data: Mapping[str, Any], name: str) -> bool:
    values = _finite_vector(data.get(name, []))
    return bool(values.size and np.any(np.isfinite(values)))


def infer_legacy_tracking_capabilities(nt_data: Mapping[str, Any]) -> frozenset[str]:
    """Infer available semantic operations from a legacy ``nt_data`` mapping."""
    capabilities: set[str] = set()
    if _has_finite_pair(nt_data, "X", "Y") or _has_finite_pair(nt_data, "CoM_X", "CoM_Y"):
        capabilities.add("position")
    if any(
        _has_finite_pair(nt_data, x_name, y_name)
        for x_name, y_name in (
            ("X", "Y"),
            ("CoM_X", "CoM_Y"),
            ("tailbase_X", "tailbase_Y"),
        )
    ):
        capabilities.add("pose_overlay")
    for field_name, capability in (
        ("alpha", "heading"),
        ("Speed", "speed"),
        ("Forward_speed", "forward_speed"),
        ("Angular_velocity", "angular_velocity"),
    ):
        if _has_finite_values(nt_data, field_name):
            capabilities.add(capability)
    return frozenset(capabilities)


@dataclass(frozen=True, eq=False)
class TrackingSample:
    """One sample selected from a tracking stream."""

    stream_id: str
    index: int
    native_time: float
    reference_time: float
    frame_index: int | None
    values: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", MappingProxyType(dict(self.values)))


@dataclass(frozen=True, eq=False)
class TrackingStream:
    """Tracking samples on one native clock, optionally mapped to reference time."""

    stream_id: str
    source_type: str
    native_times: np.ndarray
    data: Mapping[str, Any]
    clock_id: str = "reference"
    clock_transform: ClockTransform | None = None
    coordinate_system: Any = None
    camera_id: str | int | None = None
    frame_indices: np.ndarray | None = None
    capabilities: frozenset[str] = field(default_factory=frozenset)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    _reference_times: np.ndarray = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not str(self.stream_id).strip():
            raise ValueError("TrackingStream stream_id must not be empty.")
        if not str(self.source_type).strip():
            raise ValueError("TrackingStream source_type must not be empty.")
        if not str(self.clock_id).strip():
            raise ValueError("TrackingStream clock_id must not be empty.")

        native_times = _readonly_vector(self.native_times)
        if native_times.size and not np.all(np.isfinite(native_times)):
            raise ValueError("TrackingStream native_times must be finite.")
        if np.any(np.diff(native_times) < 0):
            raise ValueError("TrackingStream native_times must be ordered.")
        object.__setattr__(self, "native_times", native_times)

        if self.clock_transform is not None and self.clock_transform.source_clock != self.clock_id:
            raise ValueError("TrackingStream clock_transform must start at clock_id.")
        reference_times = (
            native_times
            if self.clock_transform is None
            else _readonly_vector(self.clock_transform.apply(native_times))
        )
        if np.any(np.diff(reference_times) < 0):
            raise ValueError("TrackingStream reference times must be ordered.")
        object.__setattr__(self, "_reference_times", reference_times)

        if self.frame_indices is not None:
            frame_indices = _readonly_vector(self.frame_indices, dtype=np.int64)
            if frame_indices.size != native_times.size:
                raise ValueError("TrackingStream frame_indices must align with native_times.")
            if np.any(np.diff(frame_indices) < 0):
                raise ValueError("TrackingStream frame_indices must be ordered.")
            object.__setattr__(self, "frame_indices", frame_indices)

        object.__setattr__(self, "data", MappingProxyType(dict(self.data)))
        object.__setattr__(self, "capabilities", frozenset(self.capabilities))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def reference_clock(self) -> str:
        if self.clock_transform is None:
            return self.clock_id
        return self.clock_transform.target_clock

    @property
    def reference_times(self) -> np.ndarray:
        return self._reference_times

    @property
    def start_reference_time(self) -> float | None:
        return float(self.reference_times[0]) if self.native_times.size else None

    @property
    def stop_reference_time(self) -> float | None:
        return float(self.reference_times[-1]) if self.native_times.size else None

    def nearest_index(self, reference_time: float, *, tolerance: float | None = None) -> int | None:
        """Return the closest sample index in reference time, subject to tolerance."""
        if tolerance is not None and tolerance < 0:
            raise ValueError("TrackingStream tolerance must be nonnegative.")
        times = self.reference_times
        if times.size == 0:
            return None
        insertion = int(np.searchsorted(times, float(reference_time), side="left"))
        candidates = [index for index in (insertion - 1, insertion) if 0 <= index < times.size]
        index = min(candidates, key=lambda candidate: (abs(times[candidate] - reference_time), candidate))
        if tolerance is not None and abs(float(times[index]) - float(reference_time)) > tolerance:
            return None
        return index

    def index_for_frame(self, frame_index: int) -> int | None:
        """Return the sample index for an exact source-video frame."""
        if self.frame_indices is None or self.frame_indices.size == 0:
            return None
        index = int(np.searchsorted(self.frame_indices, int(frame_index), side="left"))
        if index >= self.frame_indices.size or self.frame_indices[index] != int(frame_index):
            return None
        return index

    def sample(self, index: int) -> TrackingSample:
        """Return time-aligned fields from one sample index."""
        if index < 0 or index >= self.native_times.size:
            raise IndexError("TrackingStream sample index is out of range.")
        values: dict[str, Any] = {}
        for name, value in self.data.items():
            array = np.asarray(value)
            if array.ndim > 0 and array.shape[0] == self.native_times.size:
                values[name] = array[index]
        frame_index = None if self.frame_indices is None else int(self.frame_indices[index])
        return TrackingSample(
            stream_id=self.stream_id,
            index=index,
            native_time=float(self.native_times[index]),
            reference_time=float(self.reference_times[index]),
            frame_index=frame_index,
            values=values,
        )

    def sample_at(self, reference_time: float, *, tolerance: float | None = None) -> TrackingSample | None:
        """Return the sample closest to a reference time."""
        index = self.nearest_index(reference_time, tolerance=tolerance)
        return None if index is None else self.sample(index)

    def sample_for_frame(self, frame_index: int) -> TrackingSample | None:
        """Return the sample attached to an exact source-video frame."""
        index = self.index_for_frame(frame_index)
        return None if index is None else self.sample(index)


class TrackingStreamCollection(Mapping[str, TrackingStream]):
    """Named tracking streams sharing one session reference clock."""

    def __init__(
        self,
        streams: Iterable[TrackingStream] = (),
        *,
        reference_clock: str = "reference",
    ) -> None:
        if not str(reference_clock).strip():
            raise ValueError("TrackingStreamCollection reference_clock must not be empty.")
        self.reference_clock = str(reference_clock)
        self._streams: dict[str, TrackingStream] = {}
        for stream in streams:
            self.add(stream)

    def __getitem__(self, stream_id: str) -> TrackingStream:
        return self._streams[stream_id]

    def __iter__(self) -> Iterator[str]:
        return iter(self._streams)

    def __len__(self) -> int:
        return len(self._streams)

    def add(self, stream: TrackingStream) -> None:
        if stream.stream_id in self._streams:
            raise ValueError(f"Duplicate tracking stream id: {stream.stream_id}")
        if stream.reference_clock != self.reference_clock:
            raise ValueError(
                f"Tracking stream {stream.stream_id!r} uses reference clock "
                f"{stream.reference_clock!r}, expected {self.reference_clock!r}."
            )
        self._streams[stream.stream_id] = stream

    def by_camera(self, camera_id: str | int) -> tuple[TrackingStream, ...]:
        return tuple(stream for stream in self._streams.values() if stream.camera_id == camera_id)

    def with_capability(self, capability: str) -> tuple[TrackingStream, ...]:
        return tuple(stream for stream in self._streams.values() if capability in stream.capabilities)

    @property
    def reference_bounds(self) -> tuple[float, float] | None:
        starts = [stream.start_reference_time for stream in self._streams.values()]
        stops = [stream.stop_reference_time for stream in self._streams.values()]
        finite_starts = [value for value in starts if value is not None]
        finite_stops = [value for value in stops if value is not None]
        if not finite_starts or not finite_stops:
            return None
        return min(finite_starts), max(finite_stops)


def tracking_stream_from_nt_data(
    nt_data: Mapping[str, Any],
    *,
    stream_id: str = "legacy_tracking",
    source_type: str = "novitrack",
    clock_id: str = "reference",
    camera_id: str | int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> TrackingStream:
    """Expose a legacy NoviTrack ``nt_data`` mapping as a tracking stream."""
    native_times = _finite_vector(nt_data.get("Time", []))
    data = {
        name: value
        for name, value in nt_data.items()
        if name not in {"Time", "Coordinates", "schema_version"}
    }
    stream_metadata = dict(metadata or {})
    if "schema_version" in nt_data:
        stream_metadata.setdefault("schema_version", nt_data["schema_version"])
    return TrackingStream(
        stream_id=stream_id,
        source_type=source_type,
        native_times=native_times,
        data=data,
        clock_id=clock_id,
        coordinate_system=nt_data.get("Coordinates"),
        camera_id=camera_id,
        capabilities=infer_legacy_tracking_capabilities(nt_data),
        metadata=stream_metadata,
    )


__all__ = [
    "TrackingSample",
    "TrackingStream",
    "TrackingStreamCollection",
    "infer_legacy_tracking_capabilities",
    "tracking_stream_from_nt_data",
]
