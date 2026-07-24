from pathlib import Path

from novitrack.open_videos import VIDEO_EXTENSIONS, movie_search_locations
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
