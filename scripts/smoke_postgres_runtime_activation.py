from __future__ import annotations

import sys
from pathlib import Path

from ius_razon.config import AppConfig
from ius_razon.persistence.backend import (
    PersistenceBackend,
    PersistenceSettings,
)
from ius_razon.persistence.factory import build_persistence_bundle
from ius_razon.persistence.postgres_argumentation_repository import (
    PostgresArgumentationRepository,
)
from ius_razon.persistence.postgres_llm_repository import (
    PostgresLLMRepository,
)
from ius_razon.persistence.postgres_reasoning_repository import (
    PostgresReasoningRepository,
)
from ius_razon.persistence.postgres_repository import PostgresRepository
from ius_razon.persistence.postgres_runtime import load_postgres_settings
from ius_razon.services.argumentation_service import ArgumentationService
from ius_razon.services.case_service import CaseService
from ius_razon.services.llm_assistant_service import LLMAssistantService
from ius_razon.services.llm_provider import DeterministicMockProvider
from ius_razon.services.reasoning_service import ReasoningService

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    try:
        config = AppConfig.from_env(PROJECT_ROOT)
        postgres_settings = load_postgres_settings(PROJECT_ROOT)
        persistence = build_persistence_bundle(
            config=config,
            settings=PersistenceSettings(
                backend=PersistenceBackend.POSTGRES
            ),
            postgres_settings=postgres_settings,
        )

        expected = (
            (persistence.case_repository, PostgresRepository),
            (
                persistence.reasoning_repository,
                PostgresReasoningRepository,
            ),
            (
                persistence.argumentation_repository,
                PostgresArgumentationRepository,
            ),
            (persistence.llm_repository, PostgresLLMRepository),
        )
        for repository, repository_type in expected:
            if not isinstance(repository, repository_type):
                raise RuntimeError(
                    "El factory produjo un repositorio de backend incorrecto."
                )

        case_service = CaseService(
            repository=persistence.case_repository,
            config=config,
            mutation_backup=persistence.mutation_backup,
        )
        reasoning_service = ReasoningService(
            repository=persistence.reasoning_repository,
            mutation_backup=persistence.mutation_backup,
        )
        argumentation_service = ArgumentationService(
            repository=persistence.argumentation_repository,
            mutation_backup=persistence.mutation_backup,
        )
        LLMAssistantService(
            case_service=case_service,
            reasoning_service=reasoning_service,
            argumentation_service=argumentation_service,
            provider=DeterministicMockProvider(),
            repository=persistence.llm_repository,
            mutation_backup=persistence.mutation_backup,
        )

        persistence.mutation_backup.before_mutation()
    except Exception as exc:
        print(
            f"Smoke de activación PostgreSQL falló: {exc}",
            file=sys.stderr,
        )
        return 1

    print(
        "PostgreSQL runtime activation: OK | "
        "factory=postgres-only | services=OK | "
        "neon-pitr=OK | credentials=not-logged"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
