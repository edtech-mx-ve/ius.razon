from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ius_razon.config import AppConfig
from ius_razon.persistence.argumentation_repository import (
    ArgumentationRepository,
)
from ius_razon.persistence.argumentation_repository_protocol import (
    ArgumentationRepositoryProtocol,
)
from ius_razon.persistence.backend import (
    PersistenceBackend,
    PersistenceSettings,
)
from ius_razon.persistence.backup import create_database_backup
from ius_razon.persistence.case_repository import CaseRepository
from ius_razon.persistence.llm_repository import LLMRepository
from ius_razon.persistence.llm_repository_protocol import LLMRepositoryProtocol
from ius_razon.persistence.mutation_backup import (
    MutationBackup,
    NeonPitrMutationBackup,
    SQLiteMutationBackup,
)
from ius_razon.persistence.postgres_argumentation_repository import (
    PostgresArgumentationRepository,
)
from ius_razon.persistence.postgres_config import PostgresSettings
from ius_razon.persistence.postgres_llm_repository import PostgresLLMRepository
from ius_razon.persistence.postgres_reasoning_repository import (
    PostgresReasoningRepository,
)
from ius_razon.persistence.postgres_repository import PostgresRepository
from ius_razon.persistence.postgres_runtime import load_postgres_settings
from ius_razon.persistence.reasoning_repository import ReasoningRepository
from ius_razon.persistence.reasoning_repository_protocol import (
    ReasoningRepositoryProtocol,
)
from ius_razon.persistence.sqlite_repository import SQLiteRepository


@dataclass(frozen=True, slots=True)
class PersistenceBundle:
    """Conjunto atómico de repositorios y política de recuperación."""

    backend: PersistenceBackend
    case_repository: CaseRepository
    reasoning_repository: ReasoningRepositoryProtocol
    argumentation_repository: ArgumentationRepositoryProtocol
    llm_repository: LLMRepositoryProtocol
    mutation_backup: MutationBackup
    startup_backup: Path | None


def build_persistence_bundle(
    *,
    config: AppConfig,
    settings: PersistenceSettings,
    postgres_settings: PostgresSettings | None = None,
) -> PersistenceBundle:
    """Construye todas las capas con un único backend de persistencia."""

    if settings.backend is PersistenceBackend.SQLITE:
        if postgres_settings is not None:
            raise ValueError(
                "postgres_settings no puede usarse con backend SQLite."
            )
        return _build_sqlite_bundle(config)

    if settings.backend is PersistenceBackend.POSTGRES:
        resolved_postgres = postgres_settings or load_postgres_settings(
            config.project_root
        )
        return _build_postgres_bundle(resolved_postgres)

    raise ValueError(f"Backend de persistencia no soportado: {settings.backend}")


def _build_sqlite_bundle(config: AppConfig) -> PersistenceBundle:
    backup_dir = config.data_dir / "backups"
    startup_backup = create_database_backup(
        config.db_path,
        backup_dir,
    )

    case_repository = SQLiteRepository(config.db_path)
    reasoning_repository = ReasoningRepository(config.db_path)
    argumentation_repository = ArgumentationRepository(config.db_path)
    llm_repository = LLMRepository(config.db_path)

    case_repository.initialize()
    reasoning_repository.initialize()
    argumentation_repository.initialize()
    llm_repository.initialize()

    mutation_backup = SQLiteMutationBackup(
        config.db_path,
        backup_dir,
        keep=20,
    )

    return PersistenceBundle(
        backend=PersistenceBackend.SQLITE,
        case_repository=case_repository,
        reasoning_repository=reasoning_repository,
        argumentation_repository=argumentation_repository,
        llm_repository=llm_repository,
        mutation_backup=mutation_backup,
        startup_backup=startup_backup,
    )


def _build_postgres_bundle(
    settings: PostgresSettings,
) -> PersistenceBundle:
    database_url = settings.database_url

    case_repository = PostgresRepository(database_url)
    reasoning_repository = PostgresReasoningRepository(database_url)
    argumentation_repository = PostgresArgumentationRepository(database_url)
    llm_repository = PostgresLLMRepository(database_url)

    case_repository.initialize()
    reasoning_repository.initialize()
    argumentation_repository.initialize()
    llm_repository.initialize()

    mutation_backup = NeonPitrMutationBackup(
        database_url,
        restore_window_hours=6,
    )

    return PersistenceBundle(
        backend=PersistenceBackend.POSTGRES,
        case_repository=case_repository,
        reasoning_repository=reasoning_repository,
        argumentation_repository=argumentation_repository,
        llm_repository=llm_repository,
        mutation_backup=mutation_backup,
        startup_backup=None,
    )
