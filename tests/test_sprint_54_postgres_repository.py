from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from ius_razon.persistence.postgres_repository import PostgresRepository
from ius_razon.persistence.sqlite_repository import SQLiteRepository


def _public_methods(repository_type: type[object]) -> set[str]:
    return {
        name
        for name, member in inspect.getmembers(
            repository_type,
            predicate=inspect.isfunction,
        )
        if not name.startswith("_")
    }


def test_postgres_repository_preserves_sqlite_public_contract() -> None:
    assert _public_methods(PostgresRepository) == _public_methods(SQLiteRepository)


def test_postgres_repository_preserves_code_prefixes() -> None:
    assert PostgresRepository._CODE_TABLES == SQLiteRepository._CODE_TABLES


def test_postgres_repository_rejects_empty_url() -> None:
    with pytest.raises(ValueError, match="database_url"):
        PostgresRepository("  ")


def test_postgres_repository_has_no_sqlite_only_runtime_tokens() -> None:
    source_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "ius_razon"
        / "persistence"
        / "postgres_repository.py"
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
