import json
from types import SimpleNamespace

from novitrack.deeplabcut_queue import (
    discover_deeplabcut_projects,
    enqueue_deeplabcut_job,
    make_deeplabcut_manifest,
)


def test_discovers_only_immediate_deeplabcut_projects(tmp_path):
    alpha = tmp_path / "alpha"
    alpha.mkdir()
    (alpha / "config.yaml").write_text("Task: alpha\n", encoding="utf-8")
    (tmp_path / "not-a-project").mkdir()
    nested = tmp_path / "group" / "nested"
    nested.mkdir(parents=True)
    (nested / "config.yaml").write_text("Task: nested\n", encoding="utf-8")

    projects = discover_deeplabcut_projects(tmp_path)

    assert [(project.name, project.config_path) for project in projects] == [
        ("alpha", alpha / "config.yaml")
    ]


def test_enqueue_writes_atomic_versioned_manifest_and_deduplicates(tmp_path):
    video = tmp_path / "session" / "session_overhead.mp4"
    config = tmp_path / "models" / "mouse" / "config.yaml"
    manifest = make_deeplabcut_manifest(
        {"subject": "0120360", "sessionid": "session-1", "date": "2026-05-19"},
        SimpleNamespace(filename=video, camera_name="overhead"),
        config,
        job_id="job-123",
        created_at="2026-10-07T10:00:00+00:00",
    )

    first = enqueue_deeplabcut_job(tmp_path / "queue", manifest)
    second = enqueue_deeplabcut_job(tmp_path / "queue", manifest)

    assert first.created is True
    assert second.created is False
    assert first.filename == tmp_path / "queue" / "pending" / "job-123.json"
    assert second.filename == first.filename
    assert json.loads(first.filename.read_text(encoding="utf-8")) == manifest
    assert not list(first.filename.parent.glob("*.tmp"))
    assert manifest["schema_version"] == 1
    assert manifest["record"]["sessionid"] == "session-1"
    assert manifest["video_path"] == str(video)
    assert manifest["dlc_config_path"] == str(config)


def test_failed_jobs_do_not_prevent_a_retry(tmp_path):
    manifest = make_deeplabcut_manifest(
        {"sessionid": "session-1"},
        SimpleNamespace(filename=tmp_path / "video.mp4", camera_name="overhead"),
        tmp_path / "model" / "config.yaml",
        job_id="new-job",
    )
    failed = tmp_path / "queue" / "failed"
    failed.mkdir(parents=True)
    (failed / "old-job.json").write_text(json.dumps(manifest), encoding="utf-8")

    result = enqueue_deeplabcut_job(tmp_path / "queue", manifest)

    assert result.created is True
    assert result.filename.parent.name == "pending"
