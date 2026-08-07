from __future__ import annotations

import pytest

from ius_razon.persistence.backend import (
    BackendActivationError,
    PersistenceBackend,
    PersistenceSettings,
)

POOLED_URL = (
    "postgresql://ius_owner:secret@"
    "ep-example-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"
)
DIRECT_URL = (
    "postgresql://ius_owner:secret@"
    "ep-example.us-east-1.aws.neon.tech/neondb?sslmode=require"
)


def test_sqlite_is_default_and_runtime_supported() -> None:
    settings = PersistenceSettings.from_env({})

    assert settings.backend is PersistenceBackend.SQLITE
    assert settings.uses_postgres is False
    settings.require_runtime_supported()


def test_explicit_sqlite_is_runtime_supported() -> None:
    settings = PersistenceSettings.from_env(
        {"IUS_RAZON_PERSISTENCE_BACKEND": "sqlite"}
    )

    settings.require_runtime_supported()


def test_postgres_configuration_is_validated_before_activation_gate() -> None:
    settings = PersistenceSettings.from_env(
        {
            "IUS_RAZON_PERSISTENCE_BACKEND": "postgres",
            "DATABASE_URL": POOLED_URL,
            "DIRECT_DATABASE_URL": DIRECT_URL,
        }
    )

    assert settings.uses_postgres is True

    with pytest.raises(
        BackendActivationError,
        match="backend mixto",
    ):
        settings.require_runtime_supported()


def test_postgres_gate_does_not_expose_credentials() -> None:
    secret = "never-print-this-password"
    settings = PersistenceSettings.from_env(
        {
            "IUS_RAZON_PERSISTENCE_BACKEND": "postgres",
            "DATABASE_URL": (
                "postgresql://ius_owner:"
                f"{secret}@ep-example-pooler.us-east-1.aws.neon.tech/"
                "neondb?sslmode=require"
            ),
            "DIRECT_DATABASE_URL": (
                "postgresql://ius_owner:"
                f"{secret}@ep-example.us-east-1.aws.neon.tech/"
                "neondb?sslmode=require"
            ),
        }
    )

    with pytest.raises(BackendActivationError) as captured:
        settings.require_runtime_supported()

    assert secret not in str(captured.value)


def test_invalid_backend_is_rejected() -> None:
    with pytest.raises(ValueError, match="sqlite o postgres"):
        PersistenceSettings.from_env(
            {"IUS_RAZON_PERSISTENCE_BACKEND": "oracle"}
        )
