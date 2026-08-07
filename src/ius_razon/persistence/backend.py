from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from ius_razon.persistence.postgres_config import PostgresSettings


class PersistenceBackend(StrEnum):
    """Backends soportados durante la migración controlada."""

    SQLITE = "sqlite"
    POSTGRES = "postgres"


class BackendActivationError(RuntimeError):
    """Impide activar un backend incompleto de forma silenciosa."""


@dataclass(frozen=True, slots=True)
class PersistenceSettings:
    """Selecciona y valida el backend solicitado."""

    backend: PersistenceBackend

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> PersistenceSettings:
        source = environ if environ is not None else os.environ
        raw_backend = source.get(
            "IUS_RAZON_PERSISTENCE_BACKEND",
            PersistenceBackend.SQLITE.value,
        )
        normalized = raw_backend.strip().lower()

        try:
            backend = PersistenceBackend(normalized)
        except ValueError as exc:
            raise ValueError(
                "IUS_RAZON_PERSISTENCE_BACKEND debe ser sqlite o postgres."
            ) from exc

        if backend is PersistenceBackend.POSTGRES:
            PostgresSettings.from_env(source)

        return cls(backend=backend)

    @property
    def uses_postgres(self) -> bool:
        return self.backend is PersistenceBackend.POSTGRES

    def require_runtime_supported(self) -> None:
        """Bloquea PostgreSQL hasta que todas las capas usen el mismo motor."""

        if not self.uses_postgres:
            return

        raise BackendActivationError(
            "PostgreSQL fue solicitado, pero la activación completa todavía "
            "está bloqueada. CaseRepository ya dispone de PostgreSQL, mientras "
            "que razonamiento, argumentación y LLM continúan usando SQLite. "
            "IUS-Razón no permite un backend mixto."
        )
