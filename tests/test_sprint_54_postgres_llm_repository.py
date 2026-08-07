from __future__ import annotations

import inspect
import io
import re
import tokenize
from pathlib import Path

import pytest

from ius_razon.persistence.llm_repository import LLMRepository
from ius_razon.persistence.postgres_llm_repository import PostgresLLMRepository


def _public_methods(repository_type: type[object]) -> set[str]:
    return {
        name
        for name, member in inspect.getmembers(
            repository_type,
            predicate=inspect.isfunction,
        )
        if not name.startswith("_")
    }


def test_postgres_llm_preserves_sqlite_public_contract() -> None:
    assert _public_methods(PostgresLLMRepository) == _public_methods(
        LLMRepository
    )


def test_postgres_llm_rejects_empty_url() -> None:
    with pytest.raises(ValueError, match="database_url"):
        PostgresLLMRepository("  ")


def test_postgres_llm_has_no_sqlite_runtime_tokens() -> None:
    source_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "ius_razon"
        / "persistence"
        / "postgres_llm_repository.py"
    )
    source = source_path.read_text(encoding="utf-8")

    forbidden = (
        "import sqlite3",
        "sqlite3.",
        "PRAGMA ",
        "BEGIN IMMEDIATE",
        "INSERT OR IGNORE",
        ".executescript(",
        "PRAGMA table_info",
    )
    for token in forbidden:
        assert token not in source


def test_postgres_llm_uses_psycopg_placeholders_only() -> None:
    source_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "ius_razon"
        / "persistence"
        / "postgres_llm_repository.py"
    )
    source = source_path.read_text(encoding="utf-8")

    assert "%s" in source
    placeholder_re = re.compile(
        r"(?:=|!=|<>|<=|>=|<|>)\s*\?|"
        r"\?\s*(?:,|\)|$)|"
        r"LIMIT\s+\?"
    )
    reader = io.StringIO(source).readline
    pending: list[int] = []

    for token in tokenize.generate_tokens(reader):
        if (
            token.type == tokenize.STRING
            and "?" in token.string
            and placeholder_re.search(token.string)
        ):
            pending.append(token.start[0])

    assert pending == []


def test_postgres_llm_sequence_is_concurrency_guarded() -> None:
    source_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "ius_razon"
        / "persistence"
        / "postgres_llm_repository.py"
    )
    source = source_path.read_text(encoding="utf-8")

    assert "pg_advisory_xact_lock" in source
    assert "llm_draft_sequences" in source
    assert "IA-" in source
