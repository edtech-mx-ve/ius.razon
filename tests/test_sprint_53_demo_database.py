from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from ius_razon.demo_database import DEMO_CASE_TITLE, build_demo_database, main
from ius_razon.domain.enums import ConfidentialityLevel

EXPECTED_COUNTS = {
    "cases": 1,
    "parties": 2,
    "facts": 3,
    "evidence": 3,
    "fact_evidence_links": 3,
    "legal_issues": 2,
    "norms": 2,
    "jurisprudence": 1,
    "doctrine": 1,
    "issue_source_links": 4,
}


def test_build_demo_database_creates_safe_complete_dataset(tmp_path: Path) -> None:
    target = tmp_path / "ius_razon_demo.db"

    result = build_demo_database(target)

    assert result.database_name == target.name
    assert result.case_title == DEMO_CASE_TITLE
    assert result.counts == EXPECTED_COUNTS
    assert target.is_file()

    with sqlite3.connect(target) as connection:
        confidentiality = connection.execute(
            "SELECT confidentiality FROM cases"
        ).fetchone()
        attachments = connection.execute(
            """
            SELECT COUNT(*) FROM evidence
            WHERE original_file_name IS NOT NULL
               OR stored_file_name IS NOT NULL
               OR file_sha256 IS NOT NULL
               OR file_size IS NOT NULL
            """
        ).fetchone()
        synthetic_sources = connection.execute(
            """
            SELECT COUNT(*) FROM norms
            WHERE source_reference LIKE '%no corresponde a legislación vigente%'
            """
        ).fetchone()

    assert confidentiality == (ConfidentialityLevel.PUBLIC_DEMO.value,)
    assert attachments == (0,)
    assert synthetic_sources == (2,)


def test_build_demo_database_refuses_implicit_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "ius_razon_demo.db"
    build_demo_database(target)

    with pytest.raises(FileExistsError):
        build_demo_database(target)


def test_force_rebuild_replaces_database_without_duplication(tmp_path: Path) -> None:
    target = tmp_path / "ius_razon_demo.db"
    build_demo_database(target)
    rebuilt = build_demo_database(target, force=True)

    assert rebuilt.counts == EXPECTED_COUNTS
    with sqlite3.connect(target) as connection:
        assert connection.execute("SELECT COUNT(*) FROM cases").fetchone() == (1,)


def test_cli_output_omits_absolute_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "nested" / "demo.db"

    exit_code = main(["--output", str(target)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"database_name": "demo.db"' in captured.out
    assert str(tmp_path) not in captured.out
    assert captured.err == ""
