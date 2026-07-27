from pathlib import Path
import subprocess

import pytest

from novitrack.open_videos import (
    VIDEO_EXTENSIONS,
    _find_movie,
    _remux_h264_to_mp4,
    movie_search_locations,
)
from novitrack.track_behavior import _missing_movies_message


def test_movie_search_locations_lists_exact_candidates():
    record = {
        "sessionid": "session01",
        "condition": "control",
        "stimulus": "light",
    }
    params = {"nt_camera_names": ["overhead"]}

    folder, locations = movie_search_locations(
        record, params, session_path=Path("data") / "session01"
    )

    assert folder == Path("data") / "session01"
    assert len(locations["overhead"]) == 3 * len(VIDEO_EXTENSIONS)
    assert (
        folder / "session01_control_light_overhead.mp4"
        in locations["overhead"]
    )
    assert folder / "session01_overhead.MOV" in locations["overhead"]


def test_missing_movies_message_shows_folder_without_candidate_list(monkeypatch):
    folder = Path(r"\\server\share\project\subject\session01")
    candidates = [folder / "session01_overhead.mp4", folder / "session01_overhead.avi"]
    monkeypatch.setattr(
        "novitrack.track_behavior.movie_search_locations",
        lambda record, params: (folder, {"overhead": candidates}),
    )

    message = _missing_movies_message({}, {})

    assert f"Searched in: {folder}" in message
    assert "Configured cameras: overhead" in message
    assert str(candidates[0]) not in message
    assert str(candidates[1]) not in message


def test_find_movie_remuxes_h264_and_returns_mp4(monkeypatch, tmp_path):
    h264_path = tmp_path / "session01_overhead.h264"
    h264_path.write_bytes(b"raw h264")
    calls = []

    monkeypatch.setattr(
        "novitrack.open_videos.shutil.which",
        lambda name: "ffmpeg" if name == "ffmpeg" else None,
    )

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        Path(command[-1]).write_bytes(b"mp4")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("novitrack.open_videos.subprocess.run", fake_run)

    movie = _find_movie({"sessionid": "session01"}, tmp_path, "overhead")

    assert movie == tmp_path / "session01_overhead.mp4"
    assert movie.read_bytes() == b"mp4"
    assert calls[0][0][0] == "ffmpeg"
    assert calls[0][0][calls[0][0].index("-r") + 1] == "30"
    assert calls[0][1]["check"] is True


def test_find_movie_prefers_existing_mp4_without_remux(monkeypatch, tmp_path):
    mp4_path = tmp_path / "session01_overhead.mp4"
    mp4_path.write_bytes(b"mp4")
    (tmp_path / "session01_overhead.h264").write_bytes(b"raw h264")
    monkeypatch.setattr(
        "novitrack.open_videos.subprocess.run",
        lambda *args, **kwargs: pytest.fail("remux should not run"),
    )

    movie = _find_movie({"sessionid": "session01"}, tmp_path, "overhead")

    assert movie == mp4_path


def test_remux_reports_missing_conversion_tool(monkeypatch, tmp_path):
    h264_path = tmp_path / "movie.h264"
    h264_path.write_bytes(b"raw h264")
    monkeypatch.setattr("novitrack.open_videos.shutil.which", lambda name: None)

    with pytest.raises(RuntimeError, match="neither FFmpeg nor MP4Box"):
        _remux_h264_to_mp4(h264_path)


def test_remux_uses_mp4box_when_ffmpeg_is_unavailable(monkeypatch, tmp_path):
    h264_path = tmp_path / "movie.h264"
    h264_path.write_bytes(b"raw h264")
    commands = []
    monkeypatch.setattr(
        "novitrack.open_videos.shutil.which",
        lambda name: "MP4Box" if name == "MP4Box" else None,
    )

    def fake_run(command, **kwargs):
        commands.append(command)
        Path(command[-1]).write_bytes(b"mp4")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("novitrack.open_videos.subprocess.run", fake_run)

    mp4_path = _remux_h264_to_mp4(h264_path)

    assert mp4_path == h264_path.with_suffix(".mp4")
    assert commands == [
        [
            "MP4Box",
            "-add",
            f"{h264_path}:fps=30",
            "-fps",
            "original",
            "-new",
            str(mp4_path),
        ]
    ]
