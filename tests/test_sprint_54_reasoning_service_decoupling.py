from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from ius_razon.persistence.mutation_backup import (
    MutationBackup,
    NoOpMutationBackup,
    SQLiteMutationBackup,
)
from ius_razon.persistence.postgres_reasoning_repository import (
    PostgresReasoningRepository,
)
from ius_razon.persistence.reasoning_repository import ReasoningRepository
from ius_razon.persistence.reasoning_repository_protocol import (
    ReasoningRepositoryProtocol,
)
from ius_razon.services.reasoning_service import ReasoningService


def test_sqlite_reasoning_satisfies_protocol(tmp_path: Path) -> None:
    repository = ReasoningRepository(tmp_path / "reasoning.db")

    assert isinstance(repository, ReasoningRepositoryProtocol)


def test_postgres_reasoning_satisfies_protocol_without_connecting() -> None:
    repository = PostgresReasoningRepository(
        "postgresql://synthetic.invalid/ius_razon"
    )

    assert isinstance(repository, ReasoningRepositoryProtocol)


def test_backup_strategies_satisfy_mutation_protocol(tmp_path: Path) -> None:
    assert isinstance(NoOpMutationBackup(), MutationBackup)
    assert isinstance(
        SQLiteMutationBackup(
            tmp_path / "test.db",
            tmp_path / "backups",
        ),
        MutationBackup,
    )


def test_reasoning_service_requires_explicit_mutation_policy(
    tmp_path: Path,
) -> None:
    repository = ReasoningRepository(tmp_path / "reasoning.db")

    constructor = ReasoningService

    with pytest.raises(TypeError, match="mutation_backup"):
        constructor(repository)


def test_reasoning_service_accepts_explicit_noop_policy(
    tmp_path: Path,
) -> None:
    repository = ReasoningRepository(tmp_path / "reasoning.db")

    service = ReasoningService(
        repository,
        mutation_backup=NoOpMutationBackup(),
    )

    assert service is not None


def test_reasoning_service_has_no_sqlite_persistence_dependency() -> None:
    source = inspect.getsource(ReasoningService)

    forbidden = (
        "repository: ReasoningRepository,",
        "create_database_backup",
        ".db_path",
        "_backup_dir",
        "backup_dir",
    )
    for token in forbidden:
        assert token not in source
