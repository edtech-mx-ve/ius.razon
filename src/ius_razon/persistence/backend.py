from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from ius_razon.persistence.postgres_config import PostgresSettings


class PersistenceBackend(StrEnum):
    """Backends de persistencia soportados por IUS-Razón."""

    SQLITE = "sqlite"
    POSTGRES = "postgres"


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
