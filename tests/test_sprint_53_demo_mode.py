from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from ius_razon.config import AppConfig
from ius_razon.demo_database import DEMO_CASE_TITLE
from ius_razon.domain.enums import ConfidentialityLevel


def _clear_path_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for variable in (
        "IUS_RAZON_DB_PATH",
        "IUS_RAZON_DATA_DIR",
        "IUS_RAZON_DEMO_DB_PATH",
    ):
        monkeypatch.delenv(variable, raising=False)


def test_demo_mode_creates_public_dataset_without_local_persistence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_path_environment(monkeypatch)
    monkeypatch.setenv("IUS_RAZON_DEMO_MODE", "true")

    config = AppConfig.from_env(tmp_path)

    expected_db = (tmp_path / "data" / "ius_razon_demo.db").resolve()
    assert config.db_path == expected_db
    assert config.data_dir == expected_db.parent
    assert expected_db.is_file()
    assert not (tmp_path / ".ius_razon_persistence.json").exists()

    with sqlite3.connect(expected_db) as connection:
        case = connection.execute(
            "SELECT title, confidentiality FROM cases"
        ).fetchone()

    assert case == (DEMO_CASE_TITLE, ConfidentialityLevel.PUBLIC_DEMO.value)


def test_demo_mode_preserves_existing_local_persistence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_path_environment(monkeypatch)
    state_path = tmp_path / ".ius_razon_persistence.json"
    original_state = {
        "db_path": str((tmp_path / "private" / "local.db").resolve()),
        "data_dir": str((tmp_path / "private").resolve()),
    }
    state_path.write_text(json.dumps(original_state), encoding="utf-8")
    monkeypatch.setenv("IUS_RAZON_DEMO_MODE", "1")

    config = AppConfig.from_env(tmp_path)

    assert config.db_path.name == "ius_razon_demo.db"
    assert json.loads(state_path.read_text(encoding="utf-8")) == original_state


def test_demo_mode_supports_custom_relative_database_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_path_environment(monkeypatch)
    monkeypatch.setenv("IUS_RAZON_DEMO_MODE", "on")
    monkeypatch.setenv("IUS_RAZON_DEMO_DB_PATH", "runtime/public-demo.db")

    config = AppConfig.from_env(tmp_path)

    expected_db = (tmp_path / "runtime" / "public-demo.db").resolve()
    assert config.db_path == expected_db
    assert expected_db.is_file()


def test_local_mode_keeps_normal_persistence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_path_environment(monkeypatch)
    monkeypatch.delenv("IUS_RAZON_DEMO_MODE", raising=False)

    config = AppConfig.from_env(tmp_path)

    expected_db = (tmp_path / "data" / "ius_razon.db").resolve()
    assert config.db_path == expected_db
    assert not (tmp_path / "data" / "ius_razon_demo.db").exists()

    state = json.loads(
        (tmp_path / ".ius_razon_persistence.json").read_text(encoding="utf-8")
    )
    assert state["db_path"] == str(expected_db)


def test_demo_mode_rejects_ambiguous_boolean(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_path_environment(monkeypatch)
    monkeypatch.setenv("IUS_RAZON_DEMO_MODE", "quizá")

    with pytest.raises(ValueError, match="IUS_RAZON_DEMO_MODE"):
        AppConfig.from_env(tmp_path)
