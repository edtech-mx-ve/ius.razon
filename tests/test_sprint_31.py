from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

import pytest

from ius_razon.config import AppConfig
from ius_razon.domain.enums import (
    CaseStatus,
    ConfidentialityLevel,
    LegalIssueStatus,
)
from ius_razon.domain.models import CaseCreate, LegalIssueCreate
from ius_razon.domain.reasoning_models import (
    AssertionValue,
    ConditionRole,
    ReasoningAssertionCreate,
    ReasoningAssertionRecord,
    ReasoningAssertionUpdate,
    ReasoningRuleCreate,
    ReasoningRuleRecord,
    ReasoningRuleUpdate,
    RuleConditionCreate,
    RuleKind,
)
from ius_razon.persistence.reasoning_repository import (
    ReasoningConflictError,
    ReasoningRepository,
)
from ius_razon.persistence.sqlite_repository import SQLiteRepository
from ius_razon.services.case_service import CaseService
from ius_razon.services.reasoning_service import ReasoningService


def build_services(tmp_path: Path) -> tuple[CaseService, ReasoningService, AppConfig]:
    data_dir = tmp_path / "data"
    config = AppConfig(
        project_root=tmp_path,
        data_dir=data_dir,
        db_path=data_dir / "test.db",
        upload_dir=data_dir / "uploads",
        log_dir=data_dir / "logs",
        max_upload_bytes=1024 * 1024,
        log_level="INFO",
    )
    config.upload_dir.mkdir(parents=True)
    config.log_dir.mkdir(parents=True)
    case_repository = SQLiteRepository(config.db_path)
    case_repository.initialize()
    reasoning_repository = ReasoningRepository(config.db_path)
    reasoning_repository.initialize()
    return (
        CaseService(case_repository, config),
        ReasoningService(
            reasoning_repository,
            backup_dir=config.data_dir / "backups",
        ),
        config,
    )


def create_case_issue(
    case_service: CaseService,
) -> tuple[str, str]:
    case = case_service.create_case(
        CaseCreate(
            title="Caso Sprint 3.1",
            description="Caso ficticio para probar gestión segura del razonamiento.",
            matter="Mercantil",
            jurisdiction="México",
            opened_on=date.today(),
            status=CaseStatus.OPEN,
            confidentiality=ConfidentialityLevel.PUBLIC_DEMO,
        )
    )
    issue = case_service.add_legal_issue(
        LegalIssueCreate(
            case_id=case.id,
            title="Incumplimiento",
            question="¿Existió incumplimiento contractual?",
            description="Problema jurídico ficticio para pruebas.",
            status=LegalIssueStatus.OPEN,
        )
    )
    return case.id, issue.id


def add_assertion(
    service: ReasoningService,
    case_id: str,
    issue_id: str,
    *,
    key: str = "plazo_vencido",
    value: AssertionValue = AssertionValue.TRUE,
) -> ReasoningAssertionRecord:
    return service.add_assertion(
        ReasoningAssertionCreate(
            case_id=case_id,
            issue_id=issue_id,
            predicate_key=key,
            statement=f"Premisa inicial para {key}.",
            value=value,
            basis="Valoración inicial suficientemente explicada para la prueba.",
            support_codes=[],
        )
    )


def add_rule(
    service: ReasoningService,
    case_id: str,
    issue_id: str,
    *,
    prerequisite_key: str = "plazo_vencido",
    conclusion_key: str = "incumplimiento",
) -> ReasoningRuleRecord:
    return service.add_rule(
        ReasoningRuleCreate(
            case_id=case_id,
            issue_id=issue_id,
            name=f"Regla para {conclusion_key}",
            kind=RuleKind.DEFAULT,
            conclusion_key=conclusion_key,
            conclusion_statement=f"Conclusión provisional sobre {conclusion_key}.",
            conclusion_value=AssertionValue.TRUE,
            priority=100,
            active=True,
            legal_basis_codes=[],
            explanation="Puente inferencial suficientemente explicado para la prueba.",
            conditions=[
                RuleConditionCreate(
                    role=ConditionRole.PREREQUISITE,
                    predicate_key=prerequisite_key,
                    expected_value=AssertionValue.TRUE,
                )
            ],
        )
    )


def test_assertion_update_preserves_code_versions_and_backup(
    tmp_path: Path,
) -> None:
    case_service, reasoning_service, config = build_services(tmp_path)
    case_id, issue_id = create_case_issue(case_service)
    assertion = add_assertion(reasoning_service, case_id, issue_id)

    updated = reasoning_service.update_assertion(
        assertion.id,
        ReasoningAssertionUpdate(
            predicate_key="plazo_vencido",
            statement="El plazo contractual venció sin entrega.",
            value=AssertionValue.TRUE,
            basis="La fecha pactada transcurrió según el expediente de prueba.",
            support_codes=[],
        ),
    )

    assert updated.code == assertion.code
    assert updated.statement == "El plazo contractual venció sin entrega."
    versions = reasoning_service.list_assertion_versions(
        case_id=case_id,
        entity_id=assertion.id,
    )
    assert len(versions) == 1
    assert versions[0].snapshot["statement"] == assertion.statement
    assert list((config.data_dir / "backups").glob("*.db"))


def test_assertion_delete_is_blocked_when_rule_references_key(
    tmp_path: Path,
) -> None:
    case_service, reasoning_service, _ = build_services(tmp_path)
    case_id, issue_id = create_case_issue(case_service)
    assertion = add_assertion(reasoning_service, case_id, issue_id)
    add_rule(reasoning_service, case_id, issue_id)

    with pytest.raises(ReasoningConflictError, match="condición"):
        reasoning_service.delete_assertion(
            assertion.id,
            confirmation=assertion.code,
        )


def test_rule_update_preserves_code_and_can_deactivate(
    tmp_path: Path,
) -> None:
    case_service, reasoning_service, _ = build_services(tmp_path)
    case_id, issue_id = create_case_issue(case_service)
    add_assertion(reasoning_service, case_id, issue_id)
    rule = add_rule(reasoning_service, case_id, issue_id)

    updated = reasoning_service.update_rule(
        rule.id,
        ReasoningRuleUpdate(
            name="Regla corregida",
            kind=RuleKind.DEFAULT,
            conclusion_key="incumplimiento",
            conclusion_statement="Existe soporte provisional corregido.",
            conclusion_value=AssertionValue.TRUE,
            priority=200,
            active=False,
            legal_basis_codes=[],
            explanation="Explicación corregida y suficientemente detallada.",
            conditions=rule.conditions,
        ),
    )

    assert updated.code == rule.code
    assert updated.active is False
    assert updated.priority == 200
    assert reasoning_service.list_rules(
        case_id,
        issue_id,
        active_only=True,
    ) == []
    versions = reasoning_service.list_rule_versions(
        case_id=case_id,
        entity_id=rule.id,
    )
    assert versions[0].snapshot["active"] is True


def test_rule_delete_is_blocked_by_downstream_rule(
    tmp_path: Path,
) -> None:
    case_service, reasoning_service, _ = build_services(tmp_path)
    case_id, issue_id = create_case_issue(case_service)
    add_assertion(reasoning_service, case_id, issue_id)
    upstream = add_rule(
        reasoning_service,
        case_id,
        issue_id,
        conclusion_key="mora",
    )
    add_rule(
        reasoning_service,
        case_id,
        issue_id,
        prerequisite_key="mora",
        conclusion_key="responsabilidad",
    )

    with pytest.raises(ReasoningConflictError, match="otras reglas"):
        reasoning_service.delete_rule(
            upstream.id,
            confirmation=upstream.code,
        )


def test_run_snapshot_export_and_comparison_are_reproducible(
    tmp_path: Path,
) -> None:
    case_service, reasoning_service, _ = build_services(tmp_path)
    case_id, issue_id = create_case_issue(case_service)
    assertion = add_assertion(reasoning_service, case_id, issue_id)
    add_rule(reasoning_service, case_id, issue_id)

    first = reasoning_service.run(case_id=case_id, issue_id=issue_id)
    reasoning_service.update_assertion(
        assertion.id,
        ReasoningAssertionUpdate(
            predicate_key="plazo_vencido",
            statement=assertion.statement,
            value=AssertionValue.FALSE,
            basis="La revisión posterior corrige el valor para comparar ejecuciones.",
            support_codes=[],
        ),
    )
    second = reasoning_service.run(case_id=case_id, issue_id=issue_id)

    recovered = reasoning_service.get_run_report(first.run.id)
    assert recovered.run.input_snapshot["assertions"]
    assert first.run.input_hash != second.run.input_hash
    comparison = reasoning_service.compare_runs(
        first.run.id,
        second.run.id,
    )
    assert comparison["same_input"] is False
    assert "incumplimiento=Verdadero" in comparison["removed_conclusions"]
    assert comparison["changed_rule_outcomes"]

    json_export = reasoning_service.export_run_json(first.run.id)
    markdown_export = reasoning_service.export_run_markdown(first.run.id)
    assert '"input_snapshot"' in json_export
    assert first.run.input_hash in markdown_export
    assert "R-001" in markdown_export
    assert "## Resolución de conflictos" in markdown_export


def test_additive_migration_preserves_old_run_and_adds_snapshot(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    db_path = data_dir / "migration.db"
    data_dir.mkdir(parents=True)
    config = AppConfig(
        project_root=tmp_path,
        data_dir=data_dir,
        db_path=db_path,
        upload_dir=data_dir / "uploads",
        log_dir=data_dir / "logs",
        max_upload_bytes=1024 * 1024,
        log_level="INFO",
    )
    config.upload_dir.mkdir(parents=True)
    config.log_dir.mkdir(parents=True)
    case_repository = SQLiteRepository(db_path)
    case_repository.initialize()
    case_service = CaseService(case_repository, config)
    case_id, issue_id = create_case_issue(case_service)

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE reasoning_runs (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
                issue_id TEXT NOT NULL REFERENCES legal_issues(id) ON DELETE CASCADE,
                status TEXT NOT NULL,
                engine_version TEXT NOT NULL,
                input_hash TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                summary_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO reasoning_runs (
                id, case_id, issue_id, status, engine_version, input_hash,
                started_at, completed_at, summary_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-run",
                case_id,
                issue_id,
                "Completada",
                "3.0.0",
                "legacy-hash",
                "2026-08-05T00:00:00+00:00",
                "2026-08-05T00:00:01+00:00",
                '{"conclusion_count": 1}',
            ),
        )

    repository = ReasoningRepository(db_path)
    repository.initialize()

    with sqlite3.connect(db_path) as connection:
        columns = {
            str(row[1])
            for row in connection.execute(
                "PRAGMA table_info(reasoning_runs)"
            ).fetchall()
        }
        preserved = connection.execute(
            """
            SELECT input_hash, input_snapshot_json
            FROM reasoning_runs
            WHERE id = 'legacy-run'
            """
        ).fetchone()
    assert "input_snapshot_json" in columns
    assert preserved == ("legacy-hash", "{}")
