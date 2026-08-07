from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from ius_razon.persistence.argumentation_repository import ArgumentationRepository
from ius_razon.persistence.argumentation_repository_protocol import (
    ArgumentationRepositoryProtocol,
)
from ius_razon.persistence.mutation_backup import NoOpMutationBackup
from ius_razon.persistence.postgres_argumentation_repository import (
    PostgresArgumentationRepository,
)
from ius_razon.services.argumentation_service import ArgumentationService


def test_sqlite_argumentation_satisfies_protocol(tmp_path: Path) -> None:
    repository = ArgumentationRepository(tmp_path / "argumentation.db")

    assert isinstance(repository, ArgumentationRepositoryProtocol)


def test_postgres_argumentation_satisfies_protocol() -> None:
    repository = PostgresArgumentationRepository(
        "postgresql://localhost/ius_razon_test"
    )

    assert isinstance(repository, ArgumentationRepositoryProtocol)


def test_argumentation_service_requires_explicit_mutation_backup(
    tmp_path: Path,
) -> None:
    repository = ArgumentationRepository(tmp_path / "argumentation.db")
    constructor = ArgumentationService

    with pytest.raises(TypeError, match="mutation_backup"):
        constructor(repository)


def test_argumentation_service_accepts_noop_backup(tmp_path: Path) -> None:
    repository = ArgumentationRepository(tmp_path / "argumentation.db")

    service = ArgumentationService(
        repository=repository,
        mutation_backup=NoOpMutationBackup(),
    )

    assert isinstance(service, ArgumentationService)


def test_argumentation_service_has_no_sqlite_persistence_dependency() -> None:
    source = inspect.getsource(ArgumentationService)

    forbidden = (
        "repository: ArgumentationRepository,",
        "create_database_backup",
        ".db_path",
        "_backup_dir",
        "backup_dir",
    )
    for token in forbidden:
        assert token not in source

    assert "ArgumentationRepositoryProtocol" in source
    assert "MutationBackup" in source
