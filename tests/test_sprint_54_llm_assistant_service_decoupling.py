from __future__ import annotations

import inspect
from pathlib import Path

from ius_razon.persistence.llm_repository import LLMRepository
from ius_razon.persistence.llm_repository_protocol import LLMRepositoryProtocol
from ius_razon.persistence.postgres_llm_repository import PostgresLLMRepository
from ius_razon.services.llm_assistant_service import LLMAssistantService


def test_sqlite_llm_repository_satisfies_protocol(tmp_path: Path) -> None:
    repository = LLMRepository(tmp_path / "llm.db")

    assert isinstance(repository, LLMRepositoryProtocol)


def test_postgres_llm_repository_satisfies_protocol() -> None:
    repository = PostgresLLMRepository(
        "postgresql://localhost/ius_razon_test"
    )

    assert isinstance(repository, LLMRepositoryProtocol)


def test_llm_assistant_requires_explicit_mutation_backup() -> None:
    signature = inspect.signature(LLMAssistantService)

    assert "mutation_backup" in signature.parameters
    assert (
        signature.parameters["mutation_backup"].default
        is inspect.Parameter.empty
    )


def test_llm_assistant_has_no_sqlite_backup_dependency() -> None:
    source = inspect.getsource(LLMAssistantService)

    forbidden = (
        "repository: LLMRepository,",
        "create_database_backup",
        ".db_path",
        "_backup_dir",
        "backup_dir",
    )
    for token in forbidden:
        assert token not in source

    assert "LLMRepositoryProtocol" in source
    assert "MutationBackup" in source
