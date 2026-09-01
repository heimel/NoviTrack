"""NoviTrack-specific setup for the generic database browser."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from PyQt6.QtCore import QEventLoop, QPoint, QRect, Qt
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox, QPushButton

try:
    from IPython import get_ipython
except ImportError:  # pragma: no cover - unavailable outside IPython
    get_ipython = None

from inpythotools.database_browser import (
    DatabaseBrowser,
    RecordAction,
    _normalize_action_result,
    browse_database as _browse_database,
)

from .analyse_nttestrecord import analyse_nttestrecord
from .mat_database import load_mat_database
from .load_parameters import load_parameters
from .session_path import session_path
from .results_nttestrecord import results_nttestrecord


_OPEN_WINDOWS: list[DatabaseBrowser] = []
_LAST_WINDOW: DatabaseBrowser | None = None
_DEFAULT_TEST_DATABASE = Path(__file__).parent.parent / "test_data" / "nttestdb_examples.mat"
_RECORD_ID_FIELDS = (
    "mouse",
    "subject",
    "date",
    "epoch",
    "sessionid",
    "sessnr",
    "condition",
    "stimulus",
    "stack",
    "test",
    "datatype",
)
_DATABASE_ACTION_ICONS = {
    "Analyze": "microscope",
    "Results": "chart-line",
    "Track": "route",
}
_RESULT_FIGURE_GAP = 8
_NAVIGATION_BUTTON_NAMES = (
    "First record",
    "Previous record",
    "Next record",
    "Last record",
)


def _update_navigation_button_states(browser: Any) -> None:
    """Enable only navigation actions that can change the current record."""
    buttons = getattr(browser, "_nt_navigation_buttons", {})
    record_count = len(getattr(browser, "filtered_index", ()))
    position = getattr(browser, "position", 0)
    can_move_backward = record_count > 0 and position > 0
    can_move_forward = record_count > 0 and position < record_count - 1
    for name in ("First record", "Previous record"):
        if name in buttons:
            buttons[name].setEnabled(can_move_backward)
    for name in ("Next record", "Last record"):
        if name in buttons:
            buttons[name].setEnabled(can_move_forward)


def _install_navigation_button_states(browser: Any) -> None:
    """Keep database navigation buttons synchronized with the current row."""
    if hasattr(browser, "_nt_navigation_buttons"):
        _update_navigation_button_states(browser)
        return
    if not hasattr(browser, "findChildren") or not hasattr(browser, "_refresh_view"):
        return

    buttons = {
        button.accessibleName(): button
        for button in browser.findChildren(QPushButton)
        if button.accessibleName() in _NAVIGATION_BUTTON_NAMES
    }
    browser._nt_navigation_buttons = buttons
    original_refresh_view = browser._refresh_view

    def refresh_view_and_navigation() -> None:
        original_refresh_view()
        _update_navigation_button_states(browser)

    browser._refresh_view = refresh_view_and_navigation
    _update_navigation_button_states(browser)


def _available_screen_geometry(window: Any) -> QRect | None:
    """Return the usable geometry of the screen containing ``window``."""
    try:
        screen = window.screen()
    except (AttributeError, RuntimeError):
        screen = None
    if screen is None:
        app = QApplication.instance()
        screen = app.primaryScreen() if app is not None else None
    return screen.availableGeometry() if screen is not None else None


def _move_window_frame_to(window: Any, top_left: QPoint) -> None:
    """Move a top-level Qt window by its outer frame, including decorations."""
    frame_top_left = window.frameGeometry().topLeft()
    window.move(window.pos() + top_left - frame_top_left)


def _set_window_frame_geometry(window: Any, target: QRect) -> None:
    """Fit a top-level Qt window's outer frame inside ``target``."""
    # Create the native handle while the window is still hidden. This lets Qt
    # report the title-bar and border sizes before the first visible frame.
    if hasattr(window, "winId"):
        window.winId()
    geometry = window.geometry()
    frame = window.frameGeometry()
    left = geometry.left() - frame.left()
    top = geometry.top() - frame.top()
    right = frame.right() - geometry.right()
    bottom = frame.bottom() - geometry.bottom()
    window.setGeometry(
        target.x() + left,
        target.y() + top,
        max(1, target.width() - left - right),
        max(1, target.height() - top - bottom),
    )


def _position_browser_top_left(browser: Any) -> QRect | None:
    """Place the database browser at the top-left of its usable screen."""
    available = _available_screen_geometry(browser)
    if available is None:
        return None
    try:
        _move_window_frame_to(browser, available.topLeft())
    except (AttributeError, RuntimeError):
        return None
    return available


def _layout_result_figures(
    browser: Any,
    figures: Iterable[Any],
    *,
    gap: int = _RESULT_FIGURE_GAP,
) -> None:
    """Stack result figures in the screen area directly right of the browser."""
    available = _position_browser_top_left(browser)
    if available is None:
        return

    try:
        browser_frame = browser.frameGeometry()
        figure_x = browser_frame.right() + 1 + gap
        figure_width = available.right() - figure_x + 1
    except (AttributeError, RuntimeError):
        return
    if figure_width < 1:
        return

    target = QRect(figure_x, available.y(), figure_width, available.height())
    for figure in figures:
        manager = getattr(getattr(figure, "canvas", None), "manager", None)
        figure_window = getattr(manager, "window", None)
        if figure_window is None or not hasattr(figure_window, "setGeometry"):
            continue
        try:
            _set_window_frame_geometry(figure_window, target)
        except RuntimeError:
            # A figure may have been closed while its results were being created.
            continue


def _is_empty_import_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value == ""
    if isinstance(value, np.ndarray):
        return value.size == 0
    if isinstance(value, (list, tuple, dict)):
        return len(value) == 0
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _import_identity(record: Mapping[str, Any]) -> tuple[tuple[str, Any], ...]:
    """Return the fields used by MATLAB's ``recordfilter`` duplicate check."""
    identity: list[tuple[str, Any]] = []
    for field in _RECORD_ID_FIELDS:
        value = record.get(field)
        if _is_empty_import_value(value):
            continue
        if isinstance(value, np.generic):
            value = value.item()
        identity.append((field, value))
    return tuple(identity)


def _record_is_duplicate(record: Mapping[str, Any], db: pd.DataFrame) -> bool:
    identity = _import_identity(record)
    if not identity or db.empty:
        return False

    matches = pd.Series(True, index=db.index)
    for field, expected in identity:
        if field not in db.columns:
            return False
        matches &= db[field].map(
            lambda value: not _is_empty_import_value(value) and value == expected
        )
    return bool(matches.any())


def _records_from_json(filename: str | Path) -> pd.DataFrame:
    with Path(filename).open(encoding="utf-8") as stream:
        value = json.load(stream)
    if isinstance(value, Mapping):
        records = [dict(value)]
    elif isinstance(value, list) and all(isinstance(item, Mapping) for item in value):
        records = [dict(item) for item in value]
    else:
        raise ValueError("JSON import must contain a record or a list of records.")
    return pd.DataFrame.from_records(records)


def load_import_file(filename: str | Path) -> pd.DataFrame:
    """Load records from a MATLAB database or session JSON file."""
    filename = Path(filename)
    suffix = filename.suffix.lower()
    if suffix == ".mat":
        return load_mat_database(filename, save_upgraded=False)
    if suffix == ".json":
        return _records_from_json(filename)
    raise ValueError(
        f"Unsupported import extension {suffix!r}. Select a .mat or .json file."
    )


def collect_session_json_files(folder: str | Path) -> pd.DataFrame:
    """Recursively collect records from files whose names end in ``session.json``."""
    records: list[dict[str, Any]] = []
    for filename in sorted(
        path
        for path in Path(folder).rglob("*")
        if path.is_file() and path.name.lower().endswith("session.json")
    ):
        imported = _records_from_json(filename)
        for record in imported.to_dict(orient="records"):
            record.setdefault("datatype", "")
            record.setdefault("measures", {})
            record.setdefault("comment", "")
            records.append(record)

    db = pd.DataFrame.from_records(records)
    return db


def _empty_like(value: Any) -> Any:
    if isinstance(value, str):
        return ""
    if isinstance(value, dict):
        return {}
    if isinstance(value, list):
        return []
    if isinstance(value, tuple):
        return ()
    if isinstance(value, np.ndarray):
        return np.array([], dtype=value.dtype)
    return np.nan


def _align_imported_columns(
    db: pd.DataFrame, imported_db: pd.DataFrame
) -> pd.DataFrame:
    """Match MATLAB ``structconvert(..., db, true)`` field alignment."""
    if db.empty:
        return imported_db.copy()

    aligned = imported_db.copy()
    for column in db.columns:
        if column in aligned.columns:
            continue
        exemplar = next(
            (
                value
                for value in db[column]
                if not _is_empty_import_value(value)
            ),
            np.nan,
        )
        aligned[column] = [_empty_like(exemplar) for _ in range(len(aligned))]
    return aligned.loc[:, list(db.columns)]


def insert_imported_records(
    db: pd.DataFrame,
    imported_db: pd.DataFrame,
    *,
    after_index: Any | None = None,
    ask_import_duplicates: Callable[[], bool] | None = None,
) -> tuple[pd.DataFrame, int]:
    """Insert imported rows after ``after_index``, returning the database and count."""
    if imported_db.empty:
        return db.copy(), 0

    imported_db = _align_imported_columns(db, imported_db)
    accepted: list[dict[str, Any]] = []
    import_duplicates: bool | None = None
    comparison_db = db.copy()
    for record in imported_db.to_dict(orient="records"):
        if _record_is_duplicate(record, comparison_db):
            if import_duplicates is None:
                import_duplicates = (
                    ask_import_duplicates() if ask_import_duplicates is not None else False
                )
            if not import_duplicates:
                continue
        accepted.append(record)
        comparison_db = pd.concat(
            [comparison_db, pd.DataFrame.from_records([record])],
            ignore_index=True,
            sort=False,
        )

    if not accepted:
        return db.copy(), 0

    position = len(db)
    if after_index is not None and after_index in db.index:
        location = db.index.get_loc(after_index)
        position = int(location) + 1 if isinstance(location, (int, np.integer)) else len(db)

    imported = pd.DataFrame.from_records(accepted)
    merged = pd.concat(
        [db.iloc[:position], imported, db.iloc[position:]],
        ignore_index=True,
        sort=False,
    )
    return merged, len(accepted)


def _ask_import_duplicates(window: DatabaseBrowser) -> bool:
    answer = QMessageBox.question(
        window,
        "Import duplicates",
        "A duplicate record was detected. Import duplicate records?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return answer == QMessageBox.StandardButton.Yes


def _import_records_into_window(
    window: DatabaseBrowser,
    imported_db: pd.DataFrame,
    source: str | Path,
) -> int:
    current_index = window.current_record_index()
    current_row_position = (
        int(window.db.index.get_loc(current_index))
        if current_index is not None and current_index in window.db.index
        else None
    )
    merged, count = insert_imported_records(
        window.db,
        imported_db,
        after_index=current_index,
        ask_import_duplicates=lambda: _ask_import_duplicates(window),
    )
    if count == 0:
        QMessageBox.information(
            window,
            "Nothing imported",
            "No new records were found to import.",
        )
        return 0

    window.db = merged
    expression = window.filter_box.text().strip()
    if expression:
        window.apply_filter()
        if (
            current_row_position is not None
            and current_row_position in window.filtered_index
        ):
            window.position = window.filtered_index.index(current_row_position)
    else:
        window.filtered_index = list(window.db.index)
        window.position = min(window.position, len(window.filtered_index) - 1)
    window._set_dirty(True)
    window._refresh_view()
    window.statusBar().showMessage(
        f"Imported {count} record{'s' if count != 1 else ''} from {source}.",
        5000,
    )
    return count


def _import_file_into_window(window: DatabaseBrowser) -> None:
    start = window.filename.parent if window.filename else Path.cwd()
    filename, _ = QFileDialog.getOpenFileName(
        window,
        "Import file",
        str(start),
        "Supported files (*.mat *.json);;MATLAB databases (*.mat);;"
        "Session JSON files (*.json);;All files (*.*)",
    )
    if not filename:
        return
    try:
        _import_records_into_window(window, load_import_file(filename), filename)
    except Exception as exc:  # pragma: no cover - GUI error path
        window._show_error("Import failed", exc)


def _import_folder_into_window(window: DatabaseBrowser) -> None:
    start = window.filename.parent if window.filename else Path.cwd()
    folder = QFileDialog.getExistingDirectory(window, "Import folder", str(start))
    if not folder:
        return
    try:
        _import_records_into_window(window, collect_session_json_files(folder), folder)
    except Exception as exc:  # pragma: no cover - GUI error path
        window._show_error("Import failed", exc)


def _show_import_dialog(window: DatabaseBrowser) -> None:
    message = QMessageBox(window)
    message.setIcon(QMessageBox.Icon.Question)
    message.setWindowTitle("Import type")
    message.setText("What do you want to import?")
    file_button = message.addButton("Single file", QMessageBox.ButtonRole.AcceptRole)
    folder_button = message.addButton("Full folder", QMessageBox.ButtonRole.AcceptRole)
    message.addButton(QMessageBox.StandardButton.Cancel)
    message.exec()
    if message.clickedButton() is file_button:
        _import_file_into_window(window)
    elif message.clickedButton() is folder_button:
        _import_folder_into_window(window)


def _install_import_button(window: DatabaseBrowser) -> None:
    """Add the NoviTrack import control beside the generic browser's Load button."""
    layout = window.centralWidget().layout().itemAt(0).layout()
    button = QPushButton(window)
    if window.load_button is not None:
        button.setFixedHeight(window.load_button.height())
    window.set_button_icon(
        button,
        "file-input",
        "Import records",
        tooltip="Import a database or session JSON records after the current record",
    )
    button.clicked.connect(lambda _checked=False: _show_import_dialog(window))
    load_position = layout.indexOf(window.load_button)
    layout.insertWidget(load_position + 1 if load_position >= 0 else 0, button)
    window.import_button = button


def _install_filter_error_help(window: DatabaseBrowser) -> None:
    """Replace traceback-heavy filter errors with concise syntax guidance."""
    original_show_error = window._show_error

    def show_error(title: str, exc: Exception) -> None:
        if title != "Filter failed":
            original_show_error(title, exc)
            return

        expression = window.filter_box.text().strip()
        QMessageBox.warning(
            window,
            "Invalid filter",
            f"The filter could not be understood:\n\n{expression}\n\n"
            "Use a column name, a comparison operator, and a value. Text values "
            "must be enclosed in quotes, and equality uses == rather than =.\n\n"
            "Examples:\n"
            "  subject == '123456'\n"
            "  project == 'NoviTrack_example_data'\n"
            "  sessnr == 2\n"
            "  subject == '123456' and sessnr >= 2\n\n"
            "Column names must match the fields shown in the database.",
        )

    window._show_error = show_error


def _show_string_values_without_quotes(window: DatabaseBrowser) -> None:
    """Render strings as editable text instead of their quoted ``repr``."""
    if getattr(window, "_nt_unquoted_string_display", False):
        return

    original_refresh_view = window._refresh_view

    def refresh_view_with_unquoted_strings() -> None:
        original_refresh_view()
        index = window.current_record_index()
        if index is None:
            return

        window._updating_table = True
        try:
            for row in range(window.table.rowCount()):
                item = window.table.item(row, 1)
                if item is None:
                    continue
                column = item.data(Qt.ItemDataRole.UserRole)
                if column is None:
                    continue
                value = window.db.at[index, column]
                if isinstance(value, str):
                    item.setText(value)
        finally:
            window._updating_table = False

    window._refresh_view = refresh_view_with_unquoted_strings
    window._nt_unquoted_string_display = True
    window._refresh_view()


def default_database_filename() -> Path:
    """Return the bundled NoviTrack example database."""
    return _DEFAULT_TEST_DATABASE


def track_behavior_record(record: pd.Series) -> Any:
    """Launch the behavior tracker lazily so normal database browsing stays light."""
    from .track_behavior import track_behavior

    browser = _LAST_WINDOW
    record_index = record.name

    def update_open_record(updated_record: Any) -> None:
        if browser is None or record_index not in browser.db.index:
            return
        values = _normalize_action_result(updated_record)
        if values is None:
            return
        for column, value in values.items():
            if column not in browser.db.columns:
                browser.db[column] = pd.Series(
                    [None] * len(browser.db),
                    index=browser.db.index,
                    dtype=object,
                )
            browser.db.at[record_index, column] = value
        browser._set_dirty(True)
        if browser.current_record_index() == record_index:
            browser._refresh_view()

    updated_record, changed = track_behavior(
        record,
        block=True,
        parent=browser,
        on_record_changed=update_open_record if browser is not None else None,
    )
    if browser is not None:
        # Marker edits were already propagated immediately, like MATLAB's
        # update_record(record, h_dbfig, true) callback.
        return None
    return updated_record if changed else None


def analyse_nttestrecord_and_show_results(record: pd.Series) -> Any:
    """Analyze a record from the GUI and then display its result figures."""
    result = analyse_nttestrecord(record)
    updated_record = _normalize_action_result(result)
    results_nttestrecord_from_gui(updated_record if updated_record is not None else record)
    return result


def results_nttestrecord_from_gui(record: pd.Series) -> Any:
    """Display result figures from the browser without restarting Qt's event loop."""
    # In interactive sessions Matplotlib otherwise exposes every new window
    # immediately, before NoviTrack has a chance to assign its final geometry.
    with plt.ioff():
        figures = results_nttestrecord(record, show=False)
    if _LAST_WINDOW is not None:
        _layout_result_figures(_LAST_WINDOW, figures)
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


def _running_in_ipython() -> bool:
    """Return True when the browser is launched from an IPython/Jupyter kernel."""
    if get_ipython is None:
        return False
    return get_ipython() is not None


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

    existing_app = QApplication.instance()
    should_block = (
        block
        if block is not None
        else (existing_app is None and not _running_in_ipython())
    )

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
        action_icons=_DATABASE_ACTION_ICONS,
        session_folder_resolver=session_path,
        window_title_prefix="NoviTrack database browser",
        font_size=font_size,
        spacing=spacing,
        block=False,
    )
    window.filter_box.setPlaceholderText("subject == '123456'")
    _show_string_values_without_quotes(window)
    _install_import_button(window)
    _install_filter_error_help(window)
    _install_navigation_button_states(window)
    _position_browser_top_left(window)
    _OPEN_WINDOWS.append(window)
    _LAST_WINDOW = window

    if should_block:
        app = QApplication.instance()
        if existing_app is None:
            app.exec()
        else:
            loop = QEventLoop()
            window.destroyed.connect(loop.quit)
            loop.exec()
    return window


NTDatabaseBrowser = DatabaseBrowser


__all__ = [
    "NTDatabaseBrowser",
    "analyse_nttestrecord_and_show_results",
    "collect_session_json_files",
    "default_database_filename",
    "experiment_db",
    "insert_imported_records",
    "load_import_file",
    "results_nttestrecord_from_gui",
    "track_behavior_record",
]
