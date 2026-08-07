from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from ius_razon.persistence.backend import PersistenceSettings
from ius_razon.persistence.postgres_config import PostgresSettings

_RUNTIME_KEYS = (
    "IUS_RAZON_PERSISTENCE_BACKEND",
    "DATABASE_URL",
    "DIRECT_DATABASE_URL",
)


def _load_local_values(project_root: Path) -> dict[str, str]:
    """Lee secretos locales permitidos sin imprimir su contenido."""

    secrets_path = project_root / ".streamlit" / "secrets.toml"
    local: dict[str, str] = {}

    if not secrets_path.is_file():
        return local

    payload: dict[str, Any]
    with secrets_path.open("rb") as handle:
        payload = tomllib.load(handle)

    for key in _RUNTIME_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            local[key] = value.strip()

    return local


def _runtime_source(project_root: Path) -> dict[str, str]:
    """Combina entorno y secretos locales con prioridad del entorno."""

    local = _load_local_values(project_root)
    source: dict[str, str] = {}

    for key in _RUNTIME_KEYS:
        environment_value = os.getenv(key)
        if environment_value is not None and environment_value.strip():
            source[key] = environment_value.strip()
            continue

        local_value = local.get(key)
        if local_value:
            source[key] = local_value

    return source


def load_postgres_settings(project_root: Path) -> PostgresSettings:
    """Carga conexiones PostgreSQL sin imprimir credenciales."""

    return PostgresSettings.from_env(_runtime_source(project_root))


def load_persistence_settings(project_root: Path) -> PersistenceSettings:
    """Carga el selector de backend y valida PostgreSQL cuando corresponde."""

    return PersistenceSettings.from_env(_runtime_source(project_root))
