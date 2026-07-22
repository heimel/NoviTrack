"""Resolve NoviTrack session folders."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from inpythotools.logmsg import logmsg


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

    networkpathbase = Path(str(_get(params, "networkpathbase")))
    if not networkpathbase.is_dir():
        logmsg(
            f"Configured networkpathbase {networkpathbase} does not exist. "
            "Change params.networkpathbase in processparams_local.py; run "
            "'from inpythotools import edit_local_config' followed by "
            "'edit_local_config()' to open that file."
        )

    path = (
        networkpathbase
        / str(_get(record, "project"))
        / "Data_collection"
        / str(_get(record, "dataset"))
        / str(_get(record, "subject"))
        / str(_get(record, "sessionid"))
    )
    return path, path.is_dir()


__all__ = ["session_path"]
