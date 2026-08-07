from __future__ import annotations

from pathlib import Path

import pytest

import ius_razon.persistence.factory as factory_module
from ius_razon.config import AppConfig
from ius_razon.persistence.argumentation_repository import (
    ArgumentationRepository,
)
from ius_razon.persistence.backend import (
    PersistenceBackend,
    PersistenceSettings,
)
from ius_razon.persistence.factory import build_persistence_bundle
from ius_razon.persistence.llm_repository import LLMRepository
from ius_razon.persistence.mutation_backup import (
    SQLiteMutationBackup,
)
from ius_razon.persistence.postgres_config import PostgresSettings
from ius_razon.persistence.reasoning_repository import ReasoningRepository
from ius_razon.persistence.sqlite_repository import SQLiteRepository


def _config(tmp_path: Path) -> AppConfig:
    data_dir = tmp_path / "data"
    upload_dir = data_dir / "uploads"
    log_dir = data_dir / "logs"
    upload_dir.mkdir(parents=True)
    log_dir.mkdir(parents=True)
    return AppConfig(
        project_root=tmp_path,
        data_dir=data_dir,
        db_path=data_dir / "test.db",
        upload_dir=upload_dir,
        log_dir=log_dir,
        max_upload_bytes=1024 * 1024,
        log_level="INFO",
    )


def _postgres_url() -> str:
    return "postgresql://" + "user" + ":" + "pass" + "@host/db"


def test_factory_builds_complete_sqlite_bundle(tmp_path: Path) -> None:
    bundle = build_persistence_bundle(
        config=_config(tmp_path),
        settings=PersistenceSettings(
            backend=PersistenceBackend.SQLITE
        ),
    )

    assert bundle.backend is PersistenceBackend.SQLITE
    assert isinstance(bundle.case_repository, SQLiteRepository)
    assert isinstance(bundle.reasoning_repository, ReasoningRepository)
    assert isinstance(
        bundle.argumentation_repository,
        ArgumentationRepository,
    )
    assert isinstance(bundle.llm_repository, LLMRepository)
    assert isinstance(bundle.mutation_backup, SQLiteMutationBackup)


def test_factory_rejects_postgres_settings_for_sqlite(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="backend SQLite"):
        build_persistence_bundle(
            config=_config(tmp_path),
            settings=PersistenceSettings(
                backend=PersistenceBackend.SQLITE
            ),
            postgres_settings=PostgresSettings(
                database_url=_postgres_url(),
                direct_database_url=_postgres_url(),
            ),
        )


def test_factory_builds_postgres_as_one_atomic_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created: list[tuple[str, str]] = []
    initialized: list[str] = []

    class FakeRepository:
        label = "base"

        def __init__(self, database_url: str) -> None:
            self.database_url = database_url
            created.append((self.label, database_url))

        def initialize(self) -> None:
            initialized.append(self.label)

    class FakeCaseRepository(FakeRepository):
        label = "case"

    class FakeReasoningRepository(FakeRepository):
        label = "reasoning"

    class FakeArgumentationRepository(FakeRepository):
        label = "argumentation"

    class FakeLLMRepository(FakeRepository):
        label = "llm"

    class FakePitr:
        def __init__(
            self,
            database_url: str,
            *,
            restore_window_hours: int,
        ) -> None:
            self.database_url = database_url
            self.restore_window_hours = restore_window_hours

        def before_mutation(self) -> None:
            return None

    monkeypatch.setattr(
        factory_module,
        "PostgresRepository",
        FakeCaseRepository,
    )
    monkeypatch.setattr(
        factory_module,
        "PostgresReasoningRepository",
        FakeReasoningRepository,
    )
    monkeypatch.setattr(
        factory_module,
        "PostgresArgumentationRepository",
        FakeArgumentationRepository,
    )
    monkeypatch.setattr(
        factory_module,
        "PostgresLLMRepository",
        FakeLLMRepository,
    )
    monkeypatch.setattr(
        factory_module,
        "NeonPitrMutationBackup",
        FakePitr,
    )

    pooled_url = _postgres_url()
    direct_url = (
        "postgresql://" + "user" + ":" + "pass" + "@direct-host/db"
    )
    bundle = build_persistence_bundle(
        config=_config(tmp_path),
        settings=PersistenceSettings(
            backend=PersistenceBackend.POSTGRES
        ),
        postgres_settings=PostgresSettings(
            database_url=pooled_url,
            direct_database_url=direct_url,
        ),
    )

    assert bundle.backend is PersistenceBackend.POSTGRES
    assert [label for label, _ in created] == [
        "case",
        "reasoning",
        "argumentation",
        "llm",
    ]
    assert {url for _, url in created} == {pooled_url}
    assert initialized == [
        "case",
        "reasoning",
        "argumentation",
        "llm",
    ]
    assert isinstance(bundle.mutation_backup, FakePitr)
    assert bundle.mutation_backup.database_url == pooled_url
    assert bundle.mutation_backup.restore_window_hours == 6
    assert bundle.startup_backup is None


def test_app_uses_factory_with_postgres_runtime_enabled() -> None:
    app_source = (
        Path(__file__).resolve().parents[1] / "app.py"
    ).read_text(encoding="utf-8")

    assert "build_persistence_bundle" in app_source
    assert "load_persistence_settings(PROJECT_ROOT)" in app_source
    assert "require_runtime_supported" not in app_source

    forbidden_constructors = (
        "SQLiteRepository(",
        "ReasoningRepository(",
        "ArgumentationRepository(",
        "LLMRepository(",
        "PostgresRepository(",
        "PostgresReasoningRepository(",
        "PostgresArgumentationRepository(",
        "PostgresLLMRepository(",
    )
    for token in forbidden_constructors:
        assert token not in app_source

    assert app_source.count(
        "mutation_backup=persistence.mutation_backup"
    ) == 4


def test_factory_module_contains_no_backend_fallback() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "ius_razon"
        / "persistence"
        / "factory.py"
    ).read_text(encoding="utf-8")

    assert "except" not in source
    assert "NoOpMutationBackup" not in source
    assert "PersistenceBackend.SQLITE" in source
    assert "PersistenceBackend.POSTGRES" in source
