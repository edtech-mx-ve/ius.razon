from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from ius_razon.persistence.backup import create_database_backup


@runtime_checkable
class MutationBackup(Protocol):
    """Política ejecutada antes de mutaciones que requieren respaldo."""

    def before_mutation(self) -> None: ...


class SQLiteMutationBackup:
    """Mantiene la política de respaldo local usada por SQLite."""

    def __init__(
        self,
        db_path: Path,
        backup_dir: Path,
        *,
        keep: int = 20,
    ) -> None:
        self._db_path = db_path
        self._backup_dir = backup_dir
        self._keep = keep

    def before_mutation(self) -> None:
        backup_path = create_database_backup(
            self._db_path,
            self._backup_dir,
            keep=self._keep,
        )
        if backup_path is None:
            raise RuntimeError(
                "No fue posible crear el respaldo previo; la operación fue cancelada."
            )
