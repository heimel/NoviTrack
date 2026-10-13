import io
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
    _TeeStream,
    _effective_config,
    _worker_status_heartbeat,
    load_worker_settings,
    main,
    process_pending_jobs,
    translate_shared_path,
    watch_pending_jobs,
)


def test_tee_stream_tolerates_late_output_after_log_is_closed():
    console = io.StringIO()
    log = io.StringIO()
    stream = _TeeStream(console, log)
    log.close()

    assert stream.write("late shutdown output") == len("late shutdown output")
    stream.flush()

    assert console.getvalue() == "late shutdown output"


def test_worker_status_heartbeat_is_published_and_removed_on_stop(tmp_path):
    queue = tmp_path / "queue"

    with _worker_status_heartbeat(queue, interval=60) as filename:
        status = json.loads(filename.read_text(encoding="utf-8"))
        assert status["state"] == "online"
        assert status["hostname"]
        assert status["pid"] > 0
        assert status["heartbeat_interval_seconds"] == 60

    assert not filename.exists()


def test_watch_mode_polls_until_interrupted(monkeypatch):
    results = iter([True, None])
    intervals = []

    monkeypatch.setattr(
        "novitrack.deeplabcut_worker.process_next_job",
        lambda *args, **kwargs: next(results),
    )

    def stop_after_first_wait(interval):
        intervals.append(interval)
        raise KeyboardInterrupt

    completed, failed = watch_pending_jobs(
        "queue",
        WorkerSettings(),
        poll_interval=2.5,
        sleep=stop_after_first_wait,
    )

    assert (completed, failed) == (1, 0)
    assert intervals == [2.5]


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


def test_worker_completes_job_and_writes_outputs_log_and_provenance(tmp_path, capsys):
    queue, video, config = _queued_job(tmp_path)
    calls = []

    def analyze(effective_config, selected_video, output_folder):
        calls.append((effective_config, selected_video, output_folder))
        (output_folder / f"{selected_video.stem}DLC_model.h5").write_bytes(b"hdf5")
        (output_folder / f"{selected_video.stem}DLC_model_meta.pickle").write_bytes(b"meta")
        print("DLC output captured in the job log")
        return "3.0.1"

    completed, failed = process_pending_jobs(queue, WorkerSettings(), analyzer=analyze)
    captured = capsys.readouterr()

    assert (completed, failed) == (1, 0)
    assert "Starting DeepLabCut job job-123" in captured.out
    assert "Processing job job-123" in captured.out
    assert f"Video: {video}" in captured.out
    assert "DLC output captured in the job log" in captured.out
    assert "Completed job job-123" in captured.out
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


def test_worker_moves_failed_job_and_records_traceback(tmp_path, capsys):
    queue, _, _ = _queued_job(tmp_path)

    completed, failed = process_pending_jobs(
        queue,
        WorkerSettings(),
        analyzer=lambda *args: (_ for _ in ()).throw(RuntimeError("GPU unavailable")),
    )
    captured = capsys.readouterr()

    assert (completed, failed) == (0, 1)
    assert "Starting DeepLabCut job job-123" in captured.out
    assert "FAILED: GPU unavailable" in captured.err
    assert "RuntimeError: GPU unavailable" in captured.err
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


def test_cli_reports_where_to_find_failure_details_and_logs(tmp_path, capsys):
    queue = tmp_path / "queue"
    pending = queue / "pending"
    pending.mkdir(parents=True)
    manifest = {
        "schema_version": 1,
        "job_id": "missing-video",
        "state": "pending",
        "video_path": str(tmp_path / "missing.mp4"),
        "session_path": str(tmp_path),
        "output_path": str(tmp_path),
        "dlc_config_path": str(tmp_path / "missing-config.yaml"),
        "camera": "overhead",
    }
    (pending / "missing-video.json").write_text(json.dumps(manifest), encoding="utf-8")

    exit_code = main(["--queue-folder", str(queue), "--once"])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "DeepLabCut queue: 0 completed, 1 failed" in output
    assert f"Failure details: {queue / 'failed'}" in output
    assert f"Job logs: {queue / 'logs'}" in output
