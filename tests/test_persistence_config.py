from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ius_razon.config import AppConfig
from ius_razon.persistence.backup import create_database_backup


def _create_db(path: Path, case_count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE cases (id TEXT PRIMARY KEY)")
        connection.executemany(
            "INSERT INTO cases (id) VALUES (?)",
            [(f"case-{index}",) for index in range(case_count)],
        )


def test_explicit_db_path_is_persisted(
    tmp_path: Path,
    monkeypatch,
) -> None:
    legacy_db = tmp_path / "data_test" / "ius_razon_test.db"
    _create_db(legacy_db, case_count=1)

    monkeypatch.setenv("IUS_RAZON_DB_PATH", str(legacy_db))
    first = AppConfig.from_env(tmp_path)
    monkeypatch.delenv("IUS_RAZON_DB_PATH")

    second = AppConfig.from_env(tmp_path)

    assert first.db_path == legacy_db.resolve()
    assert second.db_path == legacy_db.resolve()
    assert second.data_dir == legacy_db.parent.resolve()

    state = json.loads(
        (tmp_path / ".ius_razon_persistence.json").read_text(encoding="utf-8")
    )
    assert Path(state["db_path"]) == legacy_db.resolve()


def test_populated_legacy_db_is_discovered(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("IUS_RAZON_DB_PATH", raising=False)
    monkeypatch.delenv("IUS_RAZON_DATA_DIR", raising=False)

    empty_db = tmp_path / "data" / "ius_razon.db"
    populated_db = tmp_path / "data_test" / "ius_razon_test.db"
    _create_db(empty_db, case_count=0)
    _create_db(populated_db, case_count=2)

    config = AppConfig.from_env(tmp_path)

    assert config.db_path == populated_db.resolve()
    assert config.data_dir == populated_db.parent.resolve()


def test_database_backup_is_created(tmp_path: Path) -> None:
    db_path = tmp_path / "data" / "ius_razon.db"
    _create_db(db_path, case_count=1)

    backup = create_database_backup(db_path, tmp_path / "data" / "backups")

    assert backup is not None
    assert backup.is_file()
    with sqlite3.connect(backup) as connection:
        count = connection.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
    assert count == 1
