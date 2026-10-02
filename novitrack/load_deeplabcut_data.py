"""Discover and load DeepLabCut video-analysis results as tracking streams."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from .change_times import fit_clock_transform
from .tracking_stream import TrackingStream


DLC_EXTENSIONS = frozenset({".csv", ".h5", ".hdf5"})
_DLC_COORDINATES = frozenset({"x", "y", "likelihood"})


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _float_vector(value: Any) -> np.ndarray:
    try:
        return np.asarray(value, dtype=float).reshape(-1)
    except (TypeError, ValueError):
        return np.array([], dtype=float)


@dataclass(frozen=True)
class DeepLabCutSource:
    """One DLC result file associated with a source video."""

    filename: Path
    video_info: Any
    camera_id: str | int
    camera_name: str
    config_filename: Path | None = None


def _named_child(parent: Path, name: str, *, directory: bool) -> Path | None:
    if not parent.is_dir():
        return None
    for child in parent.iterdir():
        if child.name.casefold() != name.casefold():
            continue
        if child.is_dir() == directory:
            return child
    return None


def _deeplabcut_config(video_filename: Path, camera_name: str) -> Path | None:
    """Return the session-local DLC configuration associated with a camera."""
    session_folder = video_filename.parent
    dlc_folder = _named_child(session_folder, "DeepLabCut", directory=True)
    if dlc_folder is None:
        dlc_folder = _named_child(session_folder, "DLC", directory=True)
    if dlc_folder is None:
        return None
    camera_folder = _named_child(dlc_folder, camera_name, directory=True)
    for folder in (camera_folder, dlc_folder):
        if folder is None:
            continue
        config = _named_child(folder, "config.yaml", directory=False)
        if config is not None:
            return config
    return None


def discover_deeplabcut_sources(
    video_info: Iterable[Any] | Any,
) -> tuple[DeepLabCutSource, ...]:
    """Find the newest DLC CSV/HDF5 result belonging to each known video."""
    try:
        videos = list(video_info or [])
    except TypeError:
        videos = [video_info]

    sources: list[DeepLabCutSource] = []
    for fallback_index, info in enumerate(videos):
        if info is None:
            continue
        video_filename = Path(str(_get(info, "filename", "")))
        if not video_filename.name or not video_filename.parent.is_dir():
            continue
        prefix = f"{video_filename.stem}dlc".casefold()
        candidates = [
            candidate
            for candidate in video_filename.parent.iterdir()
            if candidate.is_file()
            and candidate.suffix.casefold() in DLC_EXTENSIONS
            and candidate.stem.casefold().startswith(prefix)
        ]
        if not candidates:
            continue
        # Modification time reflects the latest analysis/re-export. The name
        # makes ties deterministic, and HDF5 wins an otherwise identical tie.
        filename = max(
            candidates,
            key=lambda path: (
                path.stat().st_mtime_ns,
                path.suffix.casefold() in {".h5", ".hdf5"},
                path.name.casefold(),
            ),
        )
        camera_id = _get(info, "camera_index", fallback_index)
        camera_name = str(_get(info, "camera_name", camera_id))
        sources.append(
            DeepLabCutSource(
                filename=filename,
                video_info=info,
                camera_id=camera_id,
                camera_name=camera_name,
                config_filename=_deeplabcut_config(video_filename, camera_name),
            )
        )
    return tuple(sources)


def _read_deeplabcut_table(filename: Path) -> pd.DataFrame:
    suffix = filename.suffix.casefold()
    if suffix == ".csv":
        table = pd.read_csv(filename, header=[0, 1, 2], index_col=0)
    elif suffix in {".h5", ".hdf5"}:
        table = pd.read_hdf(filename)
    else:
        raise ValueError(f"Unsupported DeepLabCut file type: {filename.suffix}")
    if table.empty:
        raise ValueError(f"DeepLabCut file contains no samples: {filename}")
    if not isinstance(table.columns, pd.MultiIndex) or table.columns.nlevels < 3:
        raise ValueError(
            f"DeepLabCut columns must have scorer/bodypart/coordinate levels: {filename}"
        )
    return table


def _coordinate_groups(
    table: pd.DataFrame,
) -> tuple[list[tuple[tuple[str, ...], dict[str, Any]]], tuple[str, ...]]:
    groups: dict[tuple[str, ...], dict[str, Any]] = {}
    scorers: list[str] = []
    for column in table.columns:
        parts = tuple(str(part) for part in column)
        coordinate = parts[-1].casefold()
        if coordinate not in _DLC_COORDINATES:
            continue
        identity = parts[:-1]
        groups.setdefault(identity, {})[coordinate] = column
        if parts[0] not in scorers:
            scorers.append(parts[0])

    complete = [(identity, columns) for identity, columns in groups.items() if {"x", "y"} <= columns.keys()]
    if not complete:
        raise ValueError("DeepLabCut data contain no bodypart with both x and y coordinates.")
    return complete, tuple(scorers)


def _keypoint_names(identities: list[tuple[str, ...]]) -> tuple[str, ...]:
    short_names = [identity[-1] for identity in identities]
    if len(set(short_names)) == len(short_names):
        return tuple(short_names)
    # Multi-animal data may repeat bodypart names. Preserve the individual and
    # bodypart levels while omitting the scorer, which is stored separately.
    return tuple(":".join(identity[1:]) for identity in identities)


def _numeric_column(table: pd.DataFrame, column: Any) -> np.ndarray:
    """Return a numeric column without copying when it is already floating point."""
    values = table[column]
    if pd.api.types.is_numeric_dtype(values.dtype):
        return values.to_numpy(dtype=float, copy=False)
    return pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)


def _read_deeplabcut_config(filename: Path | None) -> dict[str, Any]:
    if filename is None:
        return {}
    try:
        config = yaml.safe_load(filename.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f"Could not read DeepLabCut configuration {filename}: {exc}") from exc
    return dict(config) if isinstance(config, Mapping) else {}


def _frame_indices(table: pd.DataFrame) -> tuple[np.ndarray, str, np.ndarray | None]:
    numeric = pd.to_numeric(table.index, errors="coerce").to_numpy(dtype=float)
    valid = bool(
        numeric.size
        and np.all(np.isfinite(numeric))
        and np.all(numeric >= 0)
        and np.all(numeric == np.floor(numeric))
        and np.all(np.diff(numeric) >= 0)
    )
    if valid:
        return numeric.astype(np.int64), "table_index", None
    return np.arange(len(table), dtype=np.int64), "row_number", np.asarray(table.index)


def load_deeplabcut_stream(
    source: DeepLabCutSource,
    reference_triggers: Any,
) -> TrackingStream:
    """Load one DLC result without filtering or deriving movement measures."""
    table = _read_deeplabcut_table(source.filename)
    groups, scorers = _coordinate_groups(table)
    identities = [identity for identity, _columns in groups]
    keypoint_names = _keypoint_names(identities)
    config = _read_deeplabcut_config(source.config_filename)

    # Allocate each result exactly once. Building per-keypoint arrays and then
    # stacking them temporarily doubles the memory pressure for long movies.
    keypoints = np.empty((len(table), len(groups), 2), dtype=float)
    likelihood = np.full((len(table), len(groups)), np.nan, dtype=float)
    for keypoint_index, (_identity, columns) in enumerate(groups):
        keypoints[:, keypoint_index, 0] = _numeric_column(table, columns["x"])
        keypoints[:, keypoint_index, 1] = _numeric_column(table, columns["y"])
        if "likelihood" in columns:
            likelihood[:, keypoint_index] = _numeric_column(
                table, columns["likelihood"]
            )

    frame_indices, frame_index_source, original_index = _frame_indices(table)
    framerate = float(_get(source.video_info, "framerate", 0.0))
    if not np.isfinite(framerate) or framerate <= 0:
        raise ValueError(
            f"Cannot time DeepLabCut data because the video frame rate is invalid: {framerate}"
        )
    native_times = frame_indices.astype(float) / framerate

    video_triggers = _float_vector(_get(source.video_info, "trigger_times", []))
    target_triggers = _float_vector(reference_triggers)
    if video_triggers.size == 0:
        video_triggers = np.array([0.0])
    if target_triggers.size == 0:
        target_triggers = video_triggers - video_triggers[0]
    clock_id = f"video:{source.camera_name}"
    transform = fit_clock_transform(
        video_triggers,
        target_triggers,
        source_clock=clock_id,
        target_clock="reference",
        diagnostic_label=f"DeepLabCut {source.camera_name}",
    )

    data: dict[str, Any] = {
        "keypoints": keypoints,
        "likelihood": likelihood,
    }
    if original_index is not None:
        data["source_index"] = original_index
    capabilities = {"position", "pose_overlay"}
    if np.any(np.isfinite(likelihood)):
        capabilities.add("confidence")
    skeleton: list[tuple[str, str]] = []
    for edge in config.get("skeleton", []):
        if isinstance(edge, (list, tuple)) and len(edge) == 2:
            skeleton.append((str(edge[0]), str(edge[1])))
    try:
        likelihood_cutoff = float(config.get("pcutoff", 0.6))
    except (TypeError, ValueError):
        likelihood_cutoff = 0.6

    return TrackingStream(
        stream_id=f"deeplabcut:{source.camera_name}",
        source_type="deeplabcut",
        native_times=native_times,
        data=data,
        clock_id=clock_id,
        clock_transform=transform,
        coordinate_system="video_pixels",
        camera_id=source.camera_id,
        frame_indices=frame_indices,
        capabilities=frozenset(capabilities),
        metadata={
            "source_file": str(source.filename),
            "video_file": str(_get(source.video_info, "filename", "")),
            "framerate": framerate,
            "keypoint_names": keypoint_names,
            "scorers": scorers,
            "frame_index_source": frame_index_source,
            "config_file": (
                None if source.config_filename is None else str(source.config_filename)
            ),
            "skeleton": tuple(skeleton),
            "keypoint_colormap": (
                None if config.get("colormap") is None else str(config["colormap"])
            ),
            "skeleton_color": (
                None
                if config.get("skeleton_color") is None
                else str(config["skeleton_color"])
            ),
            "likelihood_cutoff": likelihood_cutoff,
            "keypoint_size": float(config.get("dotsize", 5.0)),
        },
    )


__all__ = [
    "DLC_EXTENSIONS",
    "DeepLabCutSource",
    "discover_deeplabcut_sources",
    "load_deeplabcut_stream",
]
