from __future__ import annotations

from pathlib import Path

import pytest

from ius_razon.persistence.backend import (
    PersistenceBackend,
    PersistenceSettings,
)
from ius_razon.persistence.postgres_runtime import (
    load_persistence_settings,
)


def _pooled_url() -> str:
    return (
        "postgresql://"
        + "ius_owner:"
        + "local-test-password"
        + "@ep-example-pooler.us-east-1.aws.neon.tech/"
        + "neondb?sslmode=require"
    )


def _direct_url() -> str:
    return (
        "postgresql://"
        + "ius_owner:"
        + "local-test-password"
        + "@ep-example.us-east-1.aws.neon.tech/"
        + "neondb?sslmode=require"
    )


def test_runtime_loader_defaults_to_sqlite(tmp_path: Path) -> None:
    settings = load_persistence_settings(tmp_path)

    assert settings.backend is PersistenceBackend.SQLITE


def test_runtime_loader_reads_local_streamlit_secrets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in (
        "IUS_RAZON_PERSISTENCE_BACKEND",
        "DATABASE_URL",
        "DIRECT_DATABASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)

    secrets_dir = tmp_path / ".streamlit"
    secrets_dir.mkdir()
    secrets = (
        'IUS_RAZON_PERSISTENCE_BACKEND = "postgres"\n'
        + 'DATABASE_URL = "'
        + _pooled_url()
        + '"\n'
        + 'DIRECT_DATABASE_URL = "'
        + _direct_url()
        + '"\n'
    )
    (secrets_dir / "secrets.toml").write_text(
        secrets,
        encoding="utf-8",
    )

    settings = load_persistence_settings(tmp_path)

    assert settings.backend is PersistenceBackend.POSTGRES
    assert settings.uses_postgres is True


def test_environment_overrides_local_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secrets_dir = tmp_path / ".streamlit"
    secrets_dir.mkdir()
    (secrets_dir / "secrets.toml").write_text(
        'IUS_RAZON_PERSISTENCE_BACKEND = "sqlite"\n',
        encoding="utf-8",
    )

    monkeypatch.setenv(
        "IUS_RAZON_PERSISTENCE_BACKEND",
        "postgres",
    )
    monkeypatch.setenv("DATABASE_URL", _pooled_url())
    monkeypatch.setenv("DIRECT_DATABASE_URL", _direct_url())

    settings = load_persistence_settings(tmp_path)

    assert settings.backend is PersistenceBackend.POSTGRES


def test_app_has_no_temporary_postgres_gate() -> None:
    app_source = (
        Path(__file__).resolve().parents[1] / "app.py"
    ).read_text(encoding="utf-8")

    assert "load_persistence_settings(PROJECT_ROOT)" in app_source
    assert "require_runtime_supported" not in app_source
    assert "build_persistence_bundle(" in app_source


def test_backend_module_has_no_activation_gate() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "ius_razon"
        / "persistence"
        / "backend.py"
    ).read_text(encoding="utf-8")

    assert "class BackendActivation" not in source
    assert "require_runtime_supported" not in source


def test_postgres_settings_remain_validated() -> None:
    with pytest.raises(ValueError):
        PersistenceSettings.from_env(
            {
                "IUS_RAZON_PERSISTENCE_BACKEND": "postgres",
                "DATABASE_URL": "",
                "DIRECT_DATABASE_URL": "",
            }
        )
