from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def create_database_backup(
    db_path: Path,
    backup_dir: Path,
    *,
    keep: int = 10,
) -> Path | None:
    """Crea un respaldo SQLite consistente antes de una operación sensible.

    No genera respaldo si la base todavía no existe o está vacía.
    """

    if not db_path.is_file() or db_path.stat().st_size == 0:
        return None

    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    destination = backup_dir / f"{db_path.stem}_{timestamp}.db"

    try:
        with (
            sqlite3.connect(db_path) as source,
            sqlite3.connect(destination) as target,
        ):
            source.backup(target)
    except sqlite3.Error as exc:
        LOGGER.warning("No fue posible crear el respaldo SQLite: %s", exc)
        destination.unlink(missing_ok=True)
        return None

    _prune_backups(backup_dir, db_path.stem, keep=keep)
    return destination


def _prune_backups(backup_dir: Path, stem: str, *, keep: int) -> None:
    if keep < 1:
        return

    backups = sorted(
        backup_dir.glob(f"{stem}_*.db"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for obsolete in backups[keep:]:
        obsolete.unlink(missing_ok=True)
