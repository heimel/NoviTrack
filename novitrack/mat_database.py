"""NoviTrack-aware MATLAB database loading and measures migration."""

from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import shutil
import uuid

import pandas as pd
from inpythotools.mat_database import (
    load_mat_database as _load_mat_database,
    save_mat_database,
)

from .measures_schema import (
    CURRENT_MEASURES_VERSION,
    upgrade_database_measures,
)


def _legacy_backup_filename(filename: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = filename.with_name(
        f"{filename.stem}_legacy_{timestamp}{filename.suffix}"
    )
    count = 2
    while candidate.exists():
        candidate = filename.with_name(
            f"{filename.stem}_legacy_{timestamp}_{count}{filename.suffix}"
        )
        count += 1
    return candidate


def _validate_saved_upgrade(filename: Path, expected_rows: int) -> None:
    saved = _load_mat_database(filename)
    if len(saved) != expected_rows:
        raise ValueError(
            f"Upgraded database contains {len(saved)} records; expected {expected_rows}."
        )
    if "measures" not in saved:
        return
    for measures in saved["measures"]:
        if not isinstance(measures, dict) or not measures:
            continue
        version = measures.get("measures_version", 0)
        try:
            version = int(version)
        except (TypeError, ValueError):
            version = 0
        if version < CURRENT_MEASURES_VERSION:
            raise ValueError("An upgraded measures record was not saved at the current version.")


def _save_upgraded_database(db: pd.DataFrame, filename: Path) -> Path:
    """Back up the original bytes, then atomically replace the database."""
    backup = _legacy_backup_filename(filename)
    shutil.copy2(filename, backup)

    temporary = filename.with_name(
        f".{filename.stem}_upgrade_{uuid.uuid4().hex}{filename.suffix}"
    )
    try:
        save_mat_database(db, temporary)
        _validate_saved_upgrade(temporary, len(db))
        os.replace(temporary, filename)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return backup


def load_mat_database(
    filename: str | Path,
    *,
    save_upgraded: bool = False,
) -> pd.DataFrame:
    """Load a database and upgrade outdated NoviTrack measures records.

    By default, migration only changes the returned DataFrame; loading never
    writes to the source database. If ``save_upgraded=True`` is explicitly
    requested, the original file is copied to
    ``<stem>_legacy_<YYYYMMDD_HHMMSS>.mat`` before the upgraded database
    atomically replaces it.
    """
    filename = Path(filename)
    db = _load_mat_database(filename)
    upgraded, report = upgrade_database_measures(db)
    if not report.changed:
        return upgraded

    backup: Path | None = None
    if save_upgraded:
        backup = _save_upgraded_database(upgraded, filename)

    upgraded.attrs["measures_migration"] = report
    if backup is not None:
        upgraded.attrs["legacy_backup"] = backup

    message = (
        f"Upgraded {report.records_upgraded} record(s) and "
        f"{report.markers_upgraded} marker(s) to measures version "
        f"{CURRENT_MEASURES_VERSION}."
    )
    if backup is not None:
        message += f" Original database copied to {backup}."
    if report.unknown_markers:
        message += f" {len(report.unknown_markers)} marker(s) could not be identified."
    print(message)
    return upgraded


__all__ = ["load_mat_database", "save_mat_database"]
