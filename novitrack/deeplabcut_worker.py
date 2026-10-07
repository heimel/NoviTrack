"""DeepLabCut GPU worker for NoviTrack's shared filesystem queue.

This file deliberately has no imports from the rest of :mod:`novitrack`, so it
can be executed directly in a lean DeepLabCut Conda environment:

    python novitrack/deeplabcut_worker.py --until-empty
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import traceback
from typing import Any, Callable, Iterator, TextIO

import yaml


class WorkerSettings(dict):
    """Small attribute-access mapping compatible with processparams_local.py."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_local_function(filename: Path) -> Callable[[Any], Any] | None:
    if not filename.is_file():
        return None
    spec = importlib.util.spec_from_file_location("_novitrack_worker_local", filename)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, "processparams_local", None)


def load_worker_settings(
    *,
    yaml_file: str | Path | None = None,
    local_config_file: str | Path | None = None,
) -> WorkerSettings:
    """Load worker settings and apply an optional processparams_local override."""
    default_yaml = Path(__file__).resolve().parent.parent / "nt_default_parameters.yaml"
    filename = Path(yaml_file) if yaml_file is not None else default_yaml
    settings = WorkerSettings(yaml.safe_load(filename.read_text(encoding="utf-8")) or {})

    local_function: Callable[[Any], Any] | None = None
    if local_config_file is not None:
        local_function = _load_local_function(Path(local_config_file))
    else:
        try:
            from processparams_local import processparams_local
        except ImportError:
            processparams_local = None
        local_function = processparams_local
        if local_function is None:
            try:
                from inpythotools import ensure_local_config
            except ImportError:
                pass
            else:
                local_function = _load_local_function(Path(ensure_local_config()))
    if local_function is not None:
        updated = local_function(settings)
        if updated is not None:
            settings = WorkerSettings(updated)
    return settings


def _path_mappings(settings: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    configured = settings.get("nt_deeplabcut_path_mappings", [])
    if isinstance(configured, Mapping):
        items = configured.items()
    else:
        items = configured
    mappings: list[tuple[str, str]] = []
    for item in items:
        try:
            source, target = item
        except (TypeError, ValueError):
            continue
        source_text = str(source).rstrip("\\/")
        target_text = str(target).rstrip("\\/")
        if source_text and target_text:
            mappings.append((source_text, target_text))
    return tuple(sorted(mappings, key=lambda item: len(item[0]), reverse=True))


def translate_shared_path(value: str | Path, settings: Mapping[str, Any]) -> Path:
    """Translate a client path prefix to its VM mount prefix when configured."""
    original = str(value)
    folded = original.casefold()
    for source, target in _path_mappings(settings):
        source_folded = source.casefold()
        if folded == source_folded or folded.startswith(source_folded + "\\") or folded.startswith(source_folded + "/"):
            remainder = original[len(source) :].lstrip("\\/")
            if os.sep == "/":
                remainder = remainder.replace("\\", "/")
            else:
                remainder = remainder.replace("/", "\\")
            return Path(target) / remainder
    return Path(original)


def _write_json_atomic(filename: Path, value: Mapping[str, Any]) -> None:
    filename.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=f".{filename.stem}.",
            suffix=".tmp",
            dir=filename.parent,
            delete=False,
        ) as temporary:
            temporary_name = temporary.name
            json.dump(dict(value), temporary, indent=2, ensure_ascii=False)
            temporary.write("\n")
        os.replace(temporary_name, filename)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def _job_outputs(video: Path, output_folder: Path) -> tuple[list[Path], list[Path]]:
    prefix = f"{video.stem}dlc".casefold()
    if not output_folder.is_dir():
        return [], []
    candidates = [
        path
        for path in output_folder.iterdir()
        if path.is_file() and path.stem.casefold().startswith(prefix)
    ]
    hdf5 = sorted(
        (path for path in candidates if path.suffix.casefold() in {".h5", ".hdf5"}),
        key=lambda path: path.name.casefold(),
    )
    metadata = sorted(
        (
            path
            for path in candidates
            if path.suffix.casefold() in {".pickle", ".pkl", ".metapickle"}
        ),
        key=lambda path: path.name.casefold(),
    )
    return hdf5, metadata


def _copy_config_for_session(config: Path, session: Path, camera: str) -> Path:
    destination = session / "DLC" / camera / "config.yaml"
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    try:
        shutil.copy2(config, temporary)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


@contextmanager
def _effective_config(
    config: Path,
    settings: Mapping[str, Any],
) -> Iterator[Path]:
    """Yield a temporary config only when project_path needs VM translation."""
    contents = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
    project_path = contents.get("project_path")
    if not project_path:
        yield config
        return
    translated = translate_shared_path(str(project_path), settings)
    if str(translated) == str(project_path):
        yield config
        return
    contents["project_path"] = str(translated)
    with tempfile.TemporaryDirectory(prefix="novitrack-dlc-") as temporary_folder:
        temporary_config = Path(temporary_folder) / "config.yaml"
        temporary_config.write_text(
            yaml.safe_dump(contents, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        yield temporary_config


def _run_deeplabcut(config: Path, video: Path, output_folder: Path) -> str:
    """Run the minimal DLC 3 inference call and return its version."""
    import deeplabcut

    deeplabcut.analyze_videos(
        str(config),
        [str(video)],
        destfolder=str(output_folder),
        save_as_csv=False,
    )
    return str(getattr(deeplabcut, "__version__", "unknown"))


def _log_line(stream: TextIO, message: str) -> None:
    stream.write(f"[{_utc_now()}] {message}\n")
    stream.flush()


def _process_claimed_job(
    running_file: Path,
    queue_folder: Path,
    settings: Mapping[str, Any],
    *,
    analyzer: Callable[[Path, Path, Path], str] | None = None,
) -> bool:
    """Process a claimed manifest and move it to completed or failed."""
    job_id = running_file.stem
    logs_folder = queue_folder / "logs"
    logs_folder.mkdir(parents=True, exist_ok=True)
    log_file = logs_folder / f"{job_id}.log"
    try:
        manifest = json.loads(running_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        manifest = {"schema_version": 1, "job_id": job_id, "state": "running"}
        load_error: Exception | None = exc
    else:
        load_error = None

    manifest.update(
        {
            "state": "running",
            "started_at": _utc_now(),
            "worker": {"host": socket.gethostname(), "pid": os.getpid()},
            "log_path": str(log_file),
        }
    )
    _write_json_atomic(running_file, manifest)

    try:
        if load_error is not None:
            raise ValueError(f"Cannot read job manifest: {load_error}")
        if int(manifest.get("schema_version", 0)) != 1:
            raise ValueError(f"Unsupported queue schema {manifest.get('schema_version')!r}")

        video = translate_shared_path(str(manifest["video_path"]), settings)
        config = translate_shared_path(str(manifest["dlc_config_path"]), settings)
        session = translate_shared_path(str(manifest["session_path"]), settings)
        output_folder = translate_shared_path(str(manifest.get("output_path", session)), settings)
        camera = str(manifest.get("camera", "overhead"))
        if not video.is_file():
            raise FileNotFoundError(f"Video does not exist: {video}")
        if not config.is_file():
            raise FileNotFoundError(f"DeepLabCut config does not exist: {config}")
        output_folder.mkdir(parents=True, exist_ok=True)

        with log_file.open("a", encoding="utf-8") as log:
            _log_line(log, f"Processing job {job_id}")
            _log_line(log, f"Video: {video}")
            _log_line(log, f"Configuration: {config}")
            hdf5, metadata = _job_outputs(video, output_folder)
            skipped_existing = bool(hdf5 and metadata)
            dlc_version = "not loaded (existing output)"
            if not skipped_existing:
                runner = analyzer or _run_deeplabcut
                with _effective_config(config, settings) as effective_config:
                    _log_line(log, f"Effective configuration: {effective_config}")
                    with redirect_stdout(log), redirect_stderr(log):
                        dlc_version = runner(effective_config, video, output_folder)
                hdf5, metadata = _job_outputs(video, output_folder)
            if not hdf5:
                raise RuntimeError("DeepLabCut did not produce an HDF5 result")
            if not metadata:
                raise RuntimeError("DeepLabCut did not produce a metadata pickle")
            provenance_config = _copy_config_for_session(config, session, camera)
            _log_line(log, f"Completed job {job_id}")

        manifest.update(
            {
                "state": "completed",
                "completed_at": _utc_now(),
                "deeplabcut_version": dlc_version,
                "skipped_existing_output": skipped_existing,
                "outputs": [str(path) for path in (*hdf5, *metadata)],
                "provenance_config": str(provenance_config),
            }
        )
        manifest.pop("error", None)
        manifest.pop("traceback", None)
        _write_json_atomic(running_file, manifest)
        completed = queue_folder / "completed"
        completed.mkdir(parents=True, exist_ok=True)
        os.replace(running_file, completed / running_file.name)
        return True
    except KeyboardInterrupt:
        manifest.update({"state": "pending", "interrupted_at": _utc_now()})
        _write_json_atomic(running_file, manifest)
        pending = queue_folder / "pending"
        pending.mkdir(parents=True, exist_ok=True)
        os.replace(running_file, pending / running_file.name)
        raise
    except Exception as exc:
        failure_traceback = traceback.format_exc()
        with log_file.open("a", encoding="utf-8") as log:
            _log_line(log, f"FAILED: {exc}")
            log.write(failure_traceback)
            log.flush()
        manifest.update(
            {
                "state": "failed",
                "failed_at": _utc_now(),
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": failure_traceback,
            }
        )
        _write_json_atomic(running_file, manifest)
        failed = queue_folder / "failed"
        failed.mkdir(parents=True, exist_ok=True)
        os.replace(running_file, failed / running_file.name)
        return False


def process_next_job(
    queue_folder: str | Path,
    settings: Mapping[str, Any],
    *,
    job_id: str | None = None,
    analyzer: Callable[[Path, Path, Path], str] | None = None,
) -> bool | None:
    """Atomically claim and process one job; return None when none is pending."""
    root = Path(queue_folder)
    pending = root / "pending"
    running = root / "running"
    running.mkdir(parents=True, exist_ok=True)
    if job_id is not None:
        candidates = [pending / f"{job_id}.json"]
    elif pending.is_dir():
        candidates = sorted(
            pending.glob("*.json"),
            key=lambda path: (path.stat().st_mtime_ns, path.name.casefold()),
        )
    else:
        candidates = []

    for source in candidates:
        destination = running / source.name
        try:
            os.replace(source, destination)
        except FileNotFoundError:
            continue
        return _process_claimed_job(
            destination,
            root,
            settings,
            analyzer=analyzer,
        )
    return None


def process_pending_jobs(
    queue_folder: str | Path,
    settings: Mapping[str, Any],
    *,
    once: bool = False,
    job_id: str | None = None,
    analyzer: Callable[[Path, Path, Path], str] | None = None,
) -> tuple[int, int]:
    """Process pending work and return ``(completed, failed)`` counts."""
    completed = 0
    failed = 0
    while True:
        result = process_next_job(
            queue_folder,
            settings,
            job_id=job_id,
            analyzer=analyzer,
        )
        if result is None:
            break
        if result:
            completed += 1
        else:
            failed += 1
        if once or job_id is not None:
            break
    return completed, failed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Process NoviTrack DeepLabCut jobs")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--until-empty", action="store_true", help="process all pending jobs (default)")
    mode.add_argument("--once", action="store_true", help="process at most one pending job")
    mode.add_argument("--job", help="process one pending job ID")
    parser.add_argument("--queue-folder", help="override nt_deeplabcut_queue_folder")
    parser.add_argument("--parameters", help="override nt_default_parameters.yaml")
    parser.add_argument("--local-config", help="explicit processparams_local.py")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    settings = load_worker_settings(
        yaml_file=args.parameters,
        local_config_file=args.local_config,
    )
    queue_value = args.queue_folder or settings.get("nt_deeplabcut_queue_folder", "")
    if not queue_value:
        raise SystemExit("nt_deeplabcut_queue_folder is not configured")
    queue_folder = translate_shared_path(str(queue_value), settings)
    completed, failed = process_pending_jobs(
        queue_folder,
        settings,
        once=args.once,
        job_id=args.job,
    )
    print(f"DeepLabCut queue: {completed} completed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
