from __future__ import annotations

import pytest

from ius_razon.persistence.backend import (
    PersistenceBackend,
    PersistenceSettings,
)


def _pooled_url(secret: str = "test-password") -> str:
    return (
        "postgresql://"
        + "ius_owner:"
        + secret
        + "@ep-example-pooler.us-east-1.aws.neon.tech/"
        + "neondb?sslmode=require"
    )


def _direct_url(secret: str = "test-password") -> str:
    return (
        "postgresql://"
        + "ius_owner:"
        + secret
        + "@ep-example.us-east-1.aws.neon.tech/"
        + "neondb?sslmode=require"
    )


def test_sqlite_is_default() -> None:
    settings = PersistenceSettings.from_env({})

    assert settings.backend is PersistenceBackend.SQLITE
    assert settings.uses_postgres is False


def test_explicit_sqlite_is_supported() -> None:
    settings = PersistenceSettings.from_env(
        {"IUS_RAZON_PERSISTENCE_BACKEND": "sqlite"}
    )

    assert settings.backend is PersistenceBackend.SQLITE


def test_postgres_is_supported_when_configuration_is_valid() -> None:
    settings = PersistenceSettings.from_env(
        {
            "IUS_RAZON_PERSISTENCE_BACKEND": "postgres",
            "DATABASE_URL": _pooled_url(),
            "DIRECT_DATABASE_URL": _direct_url(),
        }
    )

    assert settings.backend is PersistenceBackend.POSTGRES
    assert settings.uses_postgres is True


def test_postgres_validation_does_not_expose_credentials() -> None:
    secret = "never-print-this-password"

    with pytest.raises(ValueError) as captured:
        PersistenceSettings.from_env(
            {
                "IUS_RAZON_PERSISTENCE_BACKEND": "postgres",
                "DATABASE_URL": _direct_url(secret),
                "DIRECT_DATABASE_URL": _direct_url(secret),
            }
        )

    assert secret not in str(captured.value)


def test_invalid_backend_is_rejected() -> None:
    with pytest.raises(ValueError, match="sqlite o postgres"):
        PersistenceSettings.from_env(
            {"IUS_RAZON_PERSISTENCE_BACKEND": "oracle"}
        )


def test_temporary_activation_gate_no_longer_exists() -> None:
    settings = PersistenceSettings.from_env({})

    assert not hasattr(settings, "require_runtime_supported")
