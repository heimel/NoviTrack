"""Client-side DeepLabCut project discovery and shared job queue writing."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from typing import Any
from uuid import uuid4


QUEUE_SCHEMA_VERSION = 1


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


@dataclass(frozen=True)
class DeepLabCutProject:
    """One selectable DeepLabCut project."""

    name: str
    config_path: Path


@dataclass(frozen=True)
class QueueResult:
    """Result of adding, or finding, one DeepLabCut queue job."""

    manifest: dict[str, Any]
    filename: Path
    created: bool


@dataclass(frozen=True)
class QueueJob:
    """One job located in a state directory of a shared queue."""

    manifest: dict[str, Any]
    filename: Path
    queue_folder: Path
    state: str


def discover_deeplabcut_projects(folder: str | Path) -> tuple[DeepLabCutProject, ...]:
    """Return projects represented by a root or immediate-child config.yaml."""
    root = Path(folder)
    if not root.is_dir():
        return ()

    configs: list[Path] = []
    root_config = root / "config.yaml"
    if root_config.is_file():
        configs.append(root_config)
    configs.extend(
        child / "config.yaml"
        for child in root.iterdir()
        if child.is_dir() and (child / "config.yaml").is_file()
    )
    return tuple(
        DeepLabCutProject(config.parent.name, config)
        for config in sorted(configs, key=lambda path: str(path).casefold())
    )


def _record_value(record: Any, name: str) -> Any:
    value = _get(record, name, "")
    if value is None:
        return ""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            value = value.item()
        except ValueError:
            pass
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def make_deeplabcut_manifest(
    record: Any,
    video_info: Any,
    config_path: str | Path,
    *,
    job_id: str | None = None,
    created_at: str | None = None,
    retry_of: str | None = None,
) -> dict[str, Any]:
    """Build the versioned interchange document consumed by the GPU worker."""
    video_path = Path(str(_get(video_info, "filename", "")))
    config = Path(config_path)
    identifier = job_id or str(uuid4())
    timestamp = created_at or datetime.now(timezone.utc).isoformat()
    manifest = {
        "schema_version": QUEUE_SCHEMA_VERSION,
        "job_id": identifier,
        "state": "pending",
        "created_at": timestamp,
        "record": {
            name: _record_value(record, name)
            for name in (
                "subject",
                "date",
                "sessionid",
                "sessnr",
                "setup",
                "condition",
                "stimulus",
            )
        },
        "camera": str(_get(video_info, "camera_name", "overhead")),
        "video_path": str(video_path),
        "session_path": str(video_path.parent),
        "output_path": str(video_path.parent),
        "dlc_config_path": str(config),
        "dlc_project_path": str(config.parent),
    }
    if retry_of:
        manifest["retry_of"] = str(retry_of)
    return manifest


def _path_key(value: Any) -> str:
    return os.path.normcase(os.path.normpath(str(value)))


def _matching_job(
    queue_folder: Path,
    video_path: Any,
    config_path: Any,
) -> tuple[dict[str, Any], Path] | None:
    wanted_video = _path_key(video_path)
    wanted_config = _path_key(config_path)
    for state in ("pending", "running", "completed"):
        state_folder = queue_folder / state
        if not state_folder.is_dir():
            continue
        for filename in state_folder.glob("*.json"):
            try:
                manifest = json.loads(filename.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            if (
                _path_key(manifest.get("video_path", "")) == wanted_video
                and _path_key(manifest.get("dlc_config_path", "")) == wanted_config
            ):
                return manifest, filename
    return None


def find_deeplabcut_job(
    queue_folders: Sequence[str | Path],
    job_id: str,
) -> QueueJob | None:
    """Locate a job by its stable ID, regardless of its current state."""
    if not job_id:
        return None
    seen: set[str] = set()
    for queue_value in queue_folders:
        queue_folder = Path(queue_value)
        key = _path_key(queue_folder)
        if not key or key in seen:
            continue
        seen.add(key)
        for state in ("pending", "running", "completed", "failed"):
            filename = queue_folder / state / f"{job_id}.json"
            if not filename.is_file():
                continue
            try:
                manifest = json.loads(filename.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            return QueueJob(manifest, filename, queue_folder, state)
    return None


def enqueue_deeplabcut_job(
    queue_folder: str | Path,
    manifest: Mapping[str, Any],
) -> QueueResult:
    """Atomically add one job, avoiding duplicate active/completed work."""
    root = Path(queue_folder)
    existing = _matching_job(
        root,
        manifest.get("video_path", ""),
        manifest.get("dlc_config_path", ""),
    )
    if existing is not None:
        existing_manifest, filename = existing
        return QueueResult(existing_manifest, filename, False)

    pending = root / "pending"
    pending.mkdir(parents=True, exist_ok=True)
    job_id = str(manifest["job_id"])
    target = pending / f"{job_id}.json"
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=f".{job_id}.",
            suffix=".tmp",
            dir=pending,
            delete=False,
        ) as temporary:
            temporary_name = temporary.name
            json.dump(dict(manifest), temporary, indent=2, ensure_ascii=False)
            temporary.write("\n")
        os.replace(temporary_name, target)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)
    return QueueResult(dict(manifest), target, True)


__all__ = [
    "DeepLabCutProject",
    "QUEUE_SCHEMA_VERSION",
    "QueueJob",
    "QueueResult",
    "discover_deeplabcut_projects",
    "enqueue_deeplabcut_job",
    "find_deeplabcut_job",
    "make_deeplabcut_manifest",
]
