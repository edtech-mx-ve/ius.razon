from __future__ import annotations

from pathlib import Path

from ius_razon.persistence.case_repository import CaseRepository
from ius_razon.persistence.mutation_backup import (
    MutationBackup,
    SQLiteMutationBackup,
)
from ius_razon.persistence.postgres_repository import PostgresRepository
from ius_razon.persistence.sqlite_repository import SQLiteRepository


def _accept_repository(repository: CaseRepository) -> CaseRepository:
    return repository


def _accept_backup(backup: MutationBackup) -> MutationBackup:
    return backup


def test_sqlite_repository_satisfies_case_repository(
    tmp_path: Path,
) -> None:
    repository = SQLiteRepository(tmp_path / "case.db")

    assert isinstance(repository, CaseRepository)
    assert _accept_repository(repository) is repository


def test_postgres_repository_satisfies_case_repository() -> None:
    repository = PostgresRepository("postgresql://user:password@example.invalid/neondb")

    assert isinstance(repository, CaseRepository)
    assert _accept_repository(repository) is repository


def test_sqlite_mutation_backup_satisfies_contract(
    tmp_path: Path,
) -> None:
    backup = SQLiteMutationBackup(
        tmp_path / "case.db",
        tmp_path / "backups",
    )

    assert isinstance(backup, MutationBackup)
    assert _accept_backup(backup) is backup


def test_case_service_no_longer_imports_sqlite_repository() -> None:
    service_path = (
        Path(__file__).resolve().parents[1] / "src" / "ius_razon" / "services" / "case_service.py"
    )
    source = service_path.read_text(encoding="utf-8")

    assert "SQLiteRepository" not in source
    assert "create_database_backup" not in source
    assert "CaseRepository" in source
    assert "MutationBackup" in source
