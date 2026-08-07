from __future__ import annotations

from pathlib import Path

import pytest

from ius_razon.persistence.backend import (
    PersistenceBackend,
    PersistenceSettings,
)
from ius_razon.persistence.postgres_schema import (
    APPLICATION_TABLES,
    METADATA_TABLE,
    SCHEMA_VERSION,
    load_schema_text,
    schema_statements,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

POOLED_URL = (
    "postgresql://owner:secret@"
    "ep-example-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"
)
DIRECT_URL = (
    "postgresql://owner:secret@"
    "ep-example.us-east-1.aws.neon.tech/neondb?sslmode=require"
)


def test_schema_covers_current_application_tables() -> None:
    assert len(APPLICATION_TABLES) == 28
    assert METADATA_TABLE == "ius_schema_metadata"
    assert SCHEMA_VERSION == "5.4.1"


def test_schema_is_idempotent_and_avoids_sqlite_runtime_commands() -> None:
    schema = load_schema_text(PROJECT_ROOT).upper()

    assert "CREATE TABLE IF NOT EXISTS" in schema
    assert "CREATE INDEX IF NOT EXISTS" in schema
    assert "PRAGMA " not in schema
    assert "BEGIN IMMEDIATE" not in schema
    assert "AUTOINCREMENT" not in schema
    assert len(schema_statements(PROJECT_ROOT)) > len(APPLICATION_TABLES)


def test_schema_contains_current_additive_columns() -> None:
    schema = load_schema_text(PROJECT_ROOT)

    assert "input_snapshot_json TEXT NOT NULL DEFAULT '{}'" in schema
    assert "provider_mode TEXT NOT NULL DEFAULT 'Simulado local'" in schema
    assert "provider_request_id TEXT" in schema
    assert "estimated_cost_usd REAL" in schema


def test_backend_defaults_to_sqlite() -> None:
    settings = PersistenceSettings.from_env({})

    assert settings.backend is PersistenceBackend.SQLITE
    assert not settings.uses_postgres


def test_backend_accepts_postgres_with_valid_connections() -> None:
    settings = PersistenceSettings.from_env(
        {
            "IUS_RAZON_PERSISTENCE_BACKEND": "postgres",
            "DATABASE_URL": POOLED_URL,
            "DIRECT_DATABASE_URL": DIRECT_URL,
        }
    )

    assert settings.backend is PersistenceBackend.POSTGRES
    assert settings.uses_postgres


def test_backend_rejects_unknown_value() -> None:
    with pytest.raises(ValueError, match="sqlite o postgres"):
        PersistenceSettings.from_env(
            {"IUS_RAZON_PERSISTENCE_BACKEND": "desconocido"}
        )


def test_postgres_backend_requires_neon_urls() -> None:
    with pytest.raises(ValueError, match="DATABASE_URL"):
        PersistenceSettings.from_env(
            {"IUS_RAZON_PERSISTENCE_BACKEND": "postgres"}
        )
