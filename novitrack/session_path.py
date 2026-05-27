"""Resolve NoviTrack session folders."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def session_path(record: Any, params: Any | None = None) -> tuple[Path, bool]:
    """Return the session folder used by NoviTrack."""
    if params is None:
        from .load_parameters import load_parameters

        params = load_parameters(record)

    path = (
        Path(str(_get(params, "networkpathbase")))
        / str(_get(record, "project"))
        / "Data_collection"
        / str(_get(record, "dataset"))
        / str(_get(record, "subject"))
        / str(_get(record, "sessionid"))
    )
    return path, path.is_dir()


__all__ = ["session_path"]
