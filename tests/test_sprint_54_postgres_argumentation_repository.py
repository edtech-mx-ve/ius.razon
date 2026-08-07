from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from ius_razon.persistence.argumentation_repository import ArgumentationRepository
from ius_razon.persistence.postgres_argumentation_repository import (
    PostgresArgumentationRepository,
)


def _public_methods(repository_type: type[object]) -> set[str]:
    return {
        name
        for name, member in inspect.getmembers(
            repository_type,
            predicate=inspect.isfunction,
        )
        if not name.startswith("_")
    }


def test_postgres_argumentation_preserves_sqlite_public_contract() -> None:
    assert _public_methods(PostgresArgumentationRepository) == _public_methods(
        ArgumentationRepository
    )


def test_postgres_argumentation_rejects_empty_url() -> None:
    with pytest.raises(ValueError, match="database_url"):
        PostgresArgumentationRepository("  ")


def test_postgres_argumentation_has_no_sqlite_runtime_tokens() -> None:
    source_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "ius_razon"
        / "persistence"
        / "postgres_argumentation_repository.py"
    )
    source = source_path.read_text(encoding="utf-8")

    forbidden = (
        "import sqlite3",
        "sqlite3.",
        "PRAGMA ",
        "BEGIN IMMEDIATE",
        "INSERT OR IGNORE",
        ".executescript(",
    )
    for token in forbidden:
        assert token not in source


def test_postgres_argumentation_uses_psycopg_placeholders() -> None:
    source_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "ius_razon"
        / "persistence"
        / "postgres_argumentation_repository.py"
    )
    source = source_path.read_text(encoding="utf-8")

    assert " %s" in source
    assert " = ?" not in source
    assert "VALUES (?" not in source


def test_postgres_argumentation_sequences_are_concurrency_guarded() -> None:
    source_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "ius_razon"
        / "persistence"
        / "postgres_argumentation_repository.py"
    )
    source = source_path.read_text(encoding="utf-8")

    assert "pg_advisory_xact_lock" in source
    assert "argument_sequences" in source
