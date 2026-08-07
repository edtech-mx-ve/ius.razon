from __future__ import annotations

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
    ReasoningRuleCreate,
    RuleConditionCreate,
    RuleKind,
)
from ius_razon.persistence.mutation_backup import SQLiteMutationBackup
from ius_razon.persistence.reasoning_repository import ReasoningRepository
from ius_razon.persistence.sqlite_repository import SQLiteRepository
from ius_razon.services.case_service import CaseService
from ius_razon.services.reasoning_service import ReasoningService


def build_services(tmp_path: Path) -> tuple[CaseService, ReasoningService]:
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
        CaseService(
            case_repository,
            config,
            mutation_backup=SQLiteMutationBackup(
                config.db_path,
                config.data_dir / "backups",
                keep=20,
            ),
        ),
        ReasoningService(reasoning_repository),
    )


def create_case_issue(
    case_service: CaseService,
) -> tuple[str, str]:
    case = case_service.create_case(
        CaseCreate(
            title="Caso de razonamiento",
            description="Caso ficticio para validar el motor jurídico.",
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
            title="Incumplimiento de entrega",
            question="¿Existió incumplimiento de la obligación de entrega?",
            description="Problema de prueba para el motor.",
            status=LegalIssueStatus.OPEN,
        )
    )
    return case.id, issue.id


def test_reasoning_migration_preserves_existing_case(tmp_path: Path) -> None:
    case_service, reasoning_service = build_services(tmp_path)
    case_id, issue_id = create_case_issue(case_service)

    assertion = reasoning_service.add_assertion(
        ReasoningAssertionCreate(
            case_id=case_id,
            issue_id=issue_id,
            predicate_key="plazo_vencido",
            statement="El plazo contractual se encuentra vencido.",
            value=AssertionValue.TRUE,
            basis="Premisa manual para prueba de persistencia.",
            support_codes=[],
        )
    )

    assert assertion.code == "A-001"
    assert case_service.get_case_summary(case_id).legal_issue_count == 1
    assert reasoning_service.list_assertions(case_id, issue_id)[0].code == "A-001"


def test_reasoning_run_is_persisted_with_trace(tmp_path: Path) -> None:
    case_service, reasoning_service = build_services(tmp_path)
    case_id, issue_id = create_case_issue(case_service)
    reasoning_service.add_assertion(
        ReasoningAssertionCreate(
            case_id=case_id,
            issue_id=issue_id,
            predicate_key="plazo_vencido",
            statement="El plazo contractual se encuentra vencido.",
            value=AssertionValue.TRUE,
            basis="Premisa manual para prueba de ejecución.",
            support_codes=[],
        )
    )
    reasoning_service.add_rule(
        ReasoningRuleCreate(
            case_id=case_id,
            issue_id=issue_id,
            name="Regla de mora",
            kind=RuleKind.DEFAULT,
            conclusion_key="mora_presunta",
            conclusion_statement="Existe una mora provisional.",
            conclusion_value=AssertionValue.TRUE,
            priority=100,
            active=True,
            legal_basis_codes=[],
            explanation="El vencimiento permite una inferencia provisional.",
            conditions=[
                RuleConditionCreate(
                    role=ConditionRole.PREREQUISITE,
                    predicate_key="plazo_vencido",
                    expected_value=AssertionValue.TRUE,
                )
            ],
        )
    )

    report = reasoning_service.run(case_id=case_id, issue_id=issue_id)

    assert len(report.conclusions) == 1
    assert len(report.traces) == 1
    recovered = reasoning_service.get_run_report(report.run.id)
    assert recovered.conclusions[0].predicate_key == "mora_presunta"
    assert recovered.run.input_hash == report.run.input_hash


def test_unknown_support_code_is_rejected(tmp_path: Path) -> None:
    case_service, reasoning_service = build_services(tmp_path)
    case_id, issue_id = create_case_issue(case_service)

    with pytest.raises(ValueError, match="P-999"):
        reasoning_service.add_assertion(
            ReasoningAssertionCreate(
                case_id=case_id,
                issue_id=issue_id,
                predicate_key="pago_acreditado",
                statement="El pago fue acreditado.",
                value=AssertionValue.TRUE,
                basis="Premisa con referencia inexistente.",
                support_codes=["P-999"],
            )
        )
