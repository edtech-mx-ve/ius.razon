from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

from ius_razon.persistence.backup import create_database_backup

LOGGER = logging.getLogger(__name__)


@runtime_checkable
class MutationBackup(Protocol):
    """Política ejecutada antes de mutaciones que requieren respaldo."""

    def before_mutation(self) -> None: ...


class NoOpMutationBackup:
    """Política explícita sin respaldo persistente, útil en pruebas."""

    def before_mutation(self) -> None:
        return None


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
class NeonPitrMutationBackup:
    """Valida un punto de recuperación WAL antes de una mutación PostgreSQL."""

    def __init__(
        self,
        database_url: str,
        *,
        restore_window_hours: int = 6,
    ) -> None:
        cleaned = database_url.strip()
        if not cleaned:
            raise ValueError("database_url no puede estar vacía.")
        if restore_window_hours < 1:
            raise ValueError(
                "restore_window_hours debe ser mayor o igual que 1."
            )
        self._database_url = cleaned
        self._restore_window_hours = restore_window_hours

    def before_mutation(self) -> None:
        connection: Connection[dict[str, Any]] | None = None
        try:
            connection = psycopg.connect(
                self._database_url,
                row_factory=dict_row,
                connect_timeout=20,
            )
            row = connection.execute(
                """
                SELECT
                    clock_timestamp() AS recovery_at,
                    pg_current_wal_lsn()::text AS wal_lsn
                """
            ).fetchone()
        except psycopg.Error as exc:
            raise RuntimeError(
                "No fue posible validar el punto de recuperación Neon PITR; "
                "la operación fue cancelada."
            ) from exc
        finally:
            if connection is not None:
                connection.close()

        if (
            row is None
            or row.get("recovery_at") is None
            or not str(row.get("wal_lsn") or "").strip()
        ):
            raise RuntimeError(
                "Neon no devolvió un punto WAL válido; "
                "la operación fue cancelada."
            )

        LOGGER.info(
            "Punto de recuperación Neon PITR validado. "
            "recovery_at=%s wal_lsn=%s configured_window_hours=%s",
            row["recovery_at"],
            row["wal_lsn"],
            self._restore_window_hours,
        )
