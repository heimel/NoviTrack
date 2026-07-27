"""Open NoviTrack behavior videos with OpenCV metadata."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
from typing import Any

import numpy as np

try:
    import cv2
except ImportError as exc:  # pragma: no cover - dependency checked at runtime
    cv2 = None
    _CV2_IMPORT_ERROR = exc
else:
    _CV2_IMPORT_ERROR = None

from inpythotools.logmsg import logmsg
from .load_parameters import load_parameters
from .load_video_triggers import load_video_triggers
from .session_path import session_path as resolve_session_path


VIDEO_EXTENSIONS = (".mp4", ".MP4", ".h264", ".avi", ".AVI", ".mov", ".MOV")


@dataclass
class VideoInfo:
    """Metadata for one NoviTrack camera movie."""

    camera_index: int
    camera_name: str
    filename: Path
    ext: str
    framerate: float
    n_frames: int
    duration: float
    width: int
    height: int
    trigger_times: np.ndarray


class OpenCVVideoReader:
    """Small seek-aware OpenCV reader optimized for sequential playback."""

    def __init__(self, info: VideoInfo) -> None:
        if cv2 is None:
            raise ImportError(
                "track_behavior needs OpenCV for smooth movie playback. "
                "Install it in the GUI environment, for example: conda install -n gui_pyqt -c conda-forge opencv"
            ) from _CV2_IMPORT_ERROR
        self.info = info
        self.capture = cv2.VideoCapture(str(info.filename))
        if not self.capture.isOpened():
            raise OSError(f"Could not open movie {info.filename}")
        self._next_frame_index = int(self.capture.get(cv2.CAP_PROP_POS_FRAMES))

    def close(self) -> None:
        self.capture.release()

    def read_at_time(self, seconds: float) -> np.ndarray | None:
        """Read the frame nearest ``seconds`` as RGB uint8."""
        seconds = max(0.0, min(float(seconds), max(0.0, self.info.duration - 1e-6)))
        target = int(round(seconds * self.info.framerate))
        target = max(0, min(target, max(0, self.info.n_frames - 1)))

        if abs(target - self._next_frame_index) > 2:
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, target)
            self._next_frame_index = target
        elif target > self._next_frame_index:
            while self._next_frame_index < target:
                ok = self.capture.grab()
                if not ok:
                    return None
                self._next_frame_index += 1

        ok, frame = self.capture.read()
        if not ok:
            return None
        self._next_frame_index = int(self.capture.get(cv2.CAP_PROP_POS_FRAMES))
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _candidate_stems(record: Any, session_path: Path, camera_name: str) -> list[Path]:
    sessionid = str(_get(record, "sessionid", ""))
    condition = str(_get(record, "condition", ""))
    stimulus = str(_get(record, "stimulus", ""))
    return [
        session_path / f"{sessionid}_{condition}_{stimulus}_{camera_name}",
        session_path / f"{sessionid}_{stimulus}_{camera_name}",
        session_path / f"{sessionid}_{camera_name}",
    ]


def movie_search_locations(
    record: Any,
    params: Any | None = None,
    *,
    session_path: str | Path | None = None,
) -> tuple[Path, dict[str, list[Path]]]:
    """Return the folder and exact movie filenames searched per camera."""
    if params is None:
        params = load_parameters(record)
    if session_path is None:
        folder, _ = resolve_session_path(record, params)
    else:
        folder = Path(session_path)

    locations = {
        str(camera_name): [
            stem.with_suffix(ext)
            for stem in _candidate_stems(record, folder, str(camera_name))
            for ext in VIDEO_EXTENSIONS
        ]
        for camera_name in _get(params, "nt_camera_names", [])
    }
    return folder, locations


def _find_movie(record: Any, session_path: Path, camera_name: str) -> Path | None:
    for stem in _candidate_stems(record, session_path, camera_name):
        for ext in VIDEO_EXTENSIONS:
            candidate = stem.with_suffix(ext)
            if candidate.exists():
                if candidate.suffix.lower() == ".h264":
                    return _remux_h264_to_mp4(candidate)
                return candidate
    return None


def _remux_h264_to_mp4(h264_path: Path, framerate: float = 30.0) -> Path:
    """Losslessly put a raw H.264 stream in an indexed MP4 container."""
    mp4_path = h264_path.with_suffix(".mp4")
    if mp4_path.exists():
        return mp4_path

    ffmpeg = shutil.which("ffmpeg")
    mp4box = shutil.which("MP4Box")
    commands: list[tuple[str, list[str]]] = []
    if ffmpeg:
        commands.append(
            (
                "FFmpeg",
                [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-r",
                    f"{framerate:g}",
                    "-i",
                    str(h264_path),
                    "-c:v",
                    "copy",
                    "-movflags",
                    "+faststart",
                    str(mp4_path),
                ],
            )
        )
    if mp4box:
        commands.append(
            (
                "MP4Box",
                [
                    mp4box,
                    "-add",
                    f"{h264_path}:fps={framerate:g}",
                    "-fps",
                    "original",
                    "-new",
                    str(mp4_path),
                ],
            )
        )

    if not commands:
        raise RuntimeError(
            f"Cannot remux {h264_path} to MP4 because neither FFmpeg nor MP4Box "
            "is installed. Install FFmpeg (recommended) or GPAC/MP4Box and try again."
        )

    logmsg(f"Remuxing movie {h264_path} to {mp4_path}")
    failures: list[str] = []
    for tool_name, command in commands:
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            mp4_path.unlink(missing_ok=True)
            detail = getattr(exc, "stderr", None) or str(exc)
            failures.append(f"{tool_name}: {str(detail).strip()}")
            continue
        if mp4_path.exists():
            logmsg(f"Created movie {mp4_path}")
            return mp4_path
        failures.append(f"{tool_name}: conversion finished without creating {mp4_path}")

    raise RuntimeError(
        f"Could not remux {h264_path} to MP4. " + " | ".join(failures)
    )


def _metadata(path: Path) -> tuple[float, int, float, int, int]:
    if cv2 is None:
        raise ImportError(
            "open_videos needs OpenCV. Install it with: conda install -n gui_pyqt -c conda-forge opencv"
        ) from _CV2_IMPORT_ERROR

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise OSError(f"Could not open movie {path}")
    framerate = float(capture.get(cv2.CAP_PROP_FPS) or 30.0)
    n_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration = n_frames / framerate if framerate > 0 and n_frames > 0 else 0.0
    capture.release()
    return framerate, n_frames, duration, width, height


def open_videos(
    record: Any,
    params: Any | None = None,
    *,
    session_path: str | Path | None = None,
) -> tuple[list[OpenCVVideoReader | None], list[VideoInfo | None], list[int]]:
    """Open all configured NoviTrack camera movies.

    Camera indices are zero-based in Python. The returned ``active_cameras``
    list therefore contains zero-based indices, unlike MATLAB.
    """
    if params is None:
        params = load_parameters(record)
    if session_path is None:
        folder, _ = resolve_session_path(record, params)
    else:
        folder = Path(session_path)

    camera_names = list(_get(params, "nt_camera_names", []))
    readers: list[OpenCVVideoReader | None] = [None] * len(camera_names)
    video_info: list[VideoInfo | None] = [None] * len(camera_names)
    active_cameras: list[int] = []

    for index, camera_name in enumerate(camera_names):
        movie = _find_movie(record, folder, str(camera_name))
        if movie is None:
            logmsg(f"Cannot find movie for camera {camera_name} in {folder}")
            continue

        framerate, n_frames, duration, width, height = _metadata(movie)
        if abs(framerate - 30.0) > 0.05:
            logmsg(f"Framerate of {movie} is {framerate:g} fps, not 30 fps.")
        triggers, _events = load_video_triggers(
            record,
            str(camera_name),
            framerate,
            params=params,
            session_path=folder,
        )
        info = VideoInfo(
            camera_index=index,
            camera_name=str(camera_name),
            filename=movie,
            ext=movie.suffix,
            framerate=framerate,
            n_frames=n_frames,
            duration=duration,
            width=width,
            height=height,
            trigger_times=triggers,
        )
        video_info[index] = info
        readers[index] = OpenCVVideoReader(info)
        active_cameras.append(index)
        logmsg(f"Opened movie {movie}")

    return readers, video_info, active_cameras


__all__ = ["OpenCVVideoReader", "VideoInfo", "movie_search_locations", "open_videos"]
