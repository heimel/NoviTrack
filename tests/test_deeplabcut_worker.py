import json
from pathlib import Path
from types import SimpleNamespace

import yaml

from novitrack.deeplabcut_queue import (
    enqueue_deeplabcut_job,
    make_deeplabcut_manifest,
)
from novitrack.deeplabcut_worker import (
    WorkerSettings,
    _effective_config,
    load_worker_settings,
    process_pending_jobs,
    translate_shared_path,
)


def _queued_job(tmp_path):
    video = tmp_path / "session" / "session_overhead.mp4"
    video.parent.mkdir()
    video.write_bytes(b"video")
    project = tmp_path / "project"
    project.mkdir()
    config = project / "config.yaml"
    config.write_text(
        yaml.safe_dump({"Task": "mouse", "project_path": str(project)}),
        encoding="utf-8",
    )
    queue = tmp_path / "queue"
    manifest = make_deeplabcut_manifest(
        {"sessionid": "session"},
        SimpleNamespace(filename=video, camera_name="overhead"),
        config,
        job_id="job-123",
        created_at="2026-10-07T10:00:00+00:00",
    )
    enqueue_deeplabcut_job(queue, manifest)
    return queue, video, config


def test_worker_completes_job_and_writes_outputs_log_and_provenance(tmp_path):
    queue, video, config = _queued_job(tmp_path)
    calls = []

    def analyze(effective_config, selected_video, output_folder):
        calls.append((effective_config, selected_video, output_folder))
        (output_folder / f"{selected_video.stem}DLC_model.h5").write_bytes(b"hdf5")
        (output_folder / f"{selected_video.stem}DLC_model_meta.pickle").write_bytes(b"meta")
        print("DLC output captured in the job log")
        return "3.0.1"

    completed, failed = process_pending_jobs(queue, WorkerSettings(), analyzer=analyze)

    assert (completed, failed) == (1, 0)
    assert len(calls) == 1
    assert calls[0][1:] == (video, video.parent)
    completed_file = queue / "completed" / "job-123.json"
    state = json.loads(completed_file.read_text(encoding="utf-8"))
    assert state["state"] == "completed"
    assert state["deeplabcut_version"] == "3.0.1"
    assert state["skipped_existing_output"] is False
    assert len(state["outputs"]) == 2
    provenance = video.parent / "DLC" / "overhead" / "config.yaml"
    assert provenance.read_bytes() == config.read_bytes()
    assert "DLC output captured" in (queue / "logs" / "job-123.log").read_text(encoding="utf-8")
    assert not (queue / "running" / "job-123.json").exists()


def test_worker_skips_inference_when_hdf5_and_metadata_already_exist(tmp_path):
    queue, video, _ = _queued_job(tmp_path)
    (video.parent / f"{video.stem}DLC_existing.h5").write_bytes(b"hdf5")
    (video.parent / f"{video.stem}DLC_existing_meta.pickle").write_bytes(b"meta")

    completed, failed = process_pending_jobs(
        queue,
        WorkerSettings(),
        analyzer=lambda *args: (_ for _ in ()).throw(AssertionError("must not run")),
    )

    assert (completed, failed) == (1, 0)
    state = json.loads((queue / "completed" / "job-123.json").read_text(encoding="utf-8"))
    assert state["skipped_existing_output"] is True
    assert state["deeplabcut_version"] == "not loaded (existing output)"


def test_worker_moves_failed_job_and_records_traceback(tmp_path):
    queue, _, _ = _queued_job(tmp_path)

    completed, failed = process_pending_jobs(
        queue,
        WorkerSettings(),
        analyzer=lambda *args: (_ for _ in ()).throw(RuntimeError("GPU unavailable")),
    )

    assert (completed, failed) == (0, 1)
    failed_file = queue / "failed" / "job-123.json"
    state = json.loads(failed_file.read_text(encoding="utf-8"))
    assert state["state"] == "failed"
    assert state["error"] == "RuntimeError: GPU unavailable"
    assert "RuntimeError: GPU unavailable" in state["traceback"]
    assert "FAILED: GPU unavailable" in (queue / "logs" / "job-123.log").read_text(encoding="utf-8")


def test_effective_config_translates_project_path_without_modifying_source(tmp_path):
    config = tmp_path / "config.yaml"
    original = {"Task": "mouse", "project_path": r"C:\client\project"}
    config.write_text(yaml.safe_dump(original), encoding="utf-8")
    settings = WorkerSettings(
        nt_deeplabcut_path_mappings=[[r"C:\client", str(tmp_path / "vm")]]
    )

    with _effective_config(config, settings) as effective:
        translated = yaml.safe_load(effective.read_text(encoding="utf-8"))
        assert effective != config
        assert Path(translated["project_path"]) == tmp_path / "vm" / "project"

    assert yaml.safe_load(config.read_text(encoding="utf-8")) == original


def test_path_mapping_and_processparams_local_override(tmp_path):
    defaults = tmp_path / "defaults.yaml"
    defaults.write_text("nt_deeplabcut_queue_folder: default\n", encoding="utf-8")
    local = tmp_path / "processparams_local.py"
    local.write_text(
        "def processparams_local(params):\n"
        "    params.nt_deeplabcut_queue_folder = r'C:\\queue'\n"
        "    params.nt_deeplabcut_path_mappings = [[r'C:\\client', r'D:\\vm']]\n"
        "    return params\n",
        encoding="utf-8",
    )

    settings = load_worker_settings(yaml_file=defaults, local_config_file=local)

    assert settings.nt_deeplabcut_queue_folder == r"C:\queue"
    assert translate_shared_path(r"C:\client\session\movie.mp4", settings) == Path(
        r"D:\vm\session\movie.mp4"
    )
