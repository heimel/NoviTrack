"""NoviTrack-specific setup for the generic database browser."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from inpythotools.database_browser import (
    DatabaseBrowser,
    RecordAction,
    _normalize_action_result,
    browse_database as _browse_database,
)

from .analyse_nttestrecord import analyse_nttestrecord
from inpythotools.mat_database import load_mat_database
from .load_parameters import load_parameters
from .session_path import session_path
from .results_nttestrecord import results_nttestrecord


_OPEN_WINDOWS: list[DatabaseBrowser] = []
_LAST_WINDOW: DatabaseBrowser | None = None
_DEFAULT_TEST_DATABASE = Path(__file__).parent.parent / "test_data" / "nttestdb_examples.mat"


def default_database_filename() -> Path:
    """Return the bundled NoviTrack example database."""
    return _DEFAULT_TEST_DATABASE


def track_behavior_record(record: pd.Series) -> Any:
    """Launch the behavior tracker lazily so normal database browsing stays light."""
    from .track_behavior import track_record

    return track_record(record)


def analyse_nttestrecord_and_show_results(record: pd.Series) -> Any:
    """Analyze a record from the GUI and then display its result figures."""
    result = analyse_nttestrecord(record)
    updated_record = _normalize_action_result(result)
    results_nttestrecord_from_gui(updated_record if updated_record is not None else record)
    return result


def results_nttestrecord_from_gui(record: pd.Series) -> Any:
    """Display result figures from the browser without restarting Qt's event loop."""
    figures = results_nttestrecord(record, show=False)
    for figure in figures:
        figure.show()
        figure.canvas.draw_idle()
        figure.canvas.flush_events()
    return figures


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _load_gui_params(yaml_file: str | Path | None = None) -> tuple[int | None, int | None]:
    try:
        params = load_parameters(yaml_file=yaml_file)
    except Exception:
        return None, None

    font_size = _as_int(params.get("fontsize", None))
    spacing = _as_int(params.get("nt_database_browser_spacing", None))
    return font_size, spacing


def _default_actions() -> dict[str, RecordAction]:
    return {
        "Analyze": analyse_nttestrecord_and_show_results,
        "Results": results_nttestrecord_from_gui,
        "Track": track_behavior_record,
    }


def experiment_db(
    db: pd.DataFrame | None = None,
    *,
    filename: str | Path | None = None,
    actions: Mapping[str, RecordAction] | None = None,
    font_size: int | None = None,
    spacing: int | None = None,
    yaml_file: str | Path | None = None,
    block: bool | None = None,
) -> DatabaseBrowser:
    """Open a NoviTrack experiment database browser and return the window instance."""
    global _LAST_WINDOW

    if db is None and filename is None:
        filename = default_database_filename()

    if db is None and filename is not None:
        db = load_mat_database(filename)

    yaml_font_size, yaml_spacing = _load_gui_params(yaml_file)
    if font_size is None:
        font_size = yaml_font_size
    if spacing is None:
        spacing = yaml_spacing

    window = _browse_database(
        db,
        filename=filename,
        actions=actions if actions is not None else _default_actions(),
        session_folder_resolver=session_path,
        window_title_prefix="NoviTrack database browser",
        font_size=font_size,
        spacing=spacing,
        block=block,
    )
    _OPEN_WINDOWS.append(window)
    _LAST_WINDOW = window
    return window


NTDatabaseBrowser = DatabaseBrowser


__all__ = [
    "NTDatabaseBrowser",
    "analyse_nttestrecord_and_show_results",
    "default_database_filename",
    "experiment_db",
    "results_nttestrecord_from_gui",
    "track_behavior_record",
]
