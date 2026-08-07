from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

import ius_razon.persistence.mutation_backup as mutation_backup_module
from ius_razon.persistence.mutation_backup import NeonPitrMutationBackup


def _test_database_url() -> str:
    return "postgresql://" + "user" + ":" + "pass" + "@host/db"


class _FakeCursor:
    def fetchone(self) -> dict[str, object]:
        return {
            "recovery_at": datetime(2026, 8, 7, 8, 0, tzinfo=UTC),
            "wal_lsn": "0/16B6C50",
        }


class _FakeConnection:
    def __init__(self) -> None:
        self.closed = False
        self.executed_sql = ""

    def execute(self, sql: str) -> _FakeCursor:
        self.executed_sql = sql
        return _FakeCursor()

    def close(self) -> None:
        self.closed = True


def test_neon_pitr_rejects_empty_url() -> None:
    with pytest.raises(ValueError, match="database_url"):
        NeonPitrMutationBackup(" ")


def test_neon_pitr_rejects_invalid_window() -> None:
    with pytest.raises(ValueError, match="restore_window_hours"):
        NeonPitrMutationBackup(
            _test_database_url(),
            restore_window_hours=0,
        )


def test_neon_pitr_records_wal_marker_without_mutating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeConnection()

    def fake_connect(*args: object, **kwargs: object) -> _FakeConnection:
        assert args[0] == _test_database_url()
        assert kwargs["connect_timeout"] == 20
        assert "row_factory" in kwargs
        return fake

    monkeypatch.setattr(
        mutation_backup_module.psycopg,
        "connect",
        fake_connect,
    )

    policy = NeonPitrMutationBackup(
        _test_database_url(),
        restore_window_hours=6,
    )
    policy.before_mutation()

    assert "clock_timestamp()" in fake.executed_sql
    assert "pg_current_wal_lsn()" in fake.executed_sql
    assert not any(
        token in fake.executed_sql.upper()
        for token in ("INSERT ", "UPDATE ", "DELETE ", "ALTER ", "DROP ")
    )
    assert fake.closed is True


def test_neon_pitr_source_does_not_print_credentials() -> None:
    source_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "ius_razon"
        / "persistence"
        / "mutation_backup.py"
    )
    source = source_path.read_text(encoding="utf-8")

    assert "class NeonPitrMutationBackup" in source
    assert "pg_current_wal_lsn" in source
    assert "print(" not in source
    assert "DIRECT_DATABASE_URL" not in source
