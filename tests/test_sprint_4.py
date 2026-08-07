from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from ius_razon.config import AppConfig
from ius_razon.domain.argumentation_models import (
    ArgumentPosition,
    ArgumentRelationCreate,
    ArgumentRelationType,
    ArgumentStatus,
    ArgumentSupportLevel,
    LegalArgumentCreate,
    LegalArgumentUpdate,
)
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
from ius_razon.persistence.argumentation_repository import (
    ArgumentationConflictError,
    ArgumentationRepository,
)
from ius_razon.persistence.mutation_backup import SQLiteMutationBackup
from ius_razon.persistence.reasoning_repository import ReasoningRepository
from ius_razon.persistence.sqlite_repository import SQLiteRepository
from ius_razon.services.argumentation_service import ArgumentationService
from ius_razon.services.case_service import CaseService
from ius_razon.services.reasoning_service import ReasoningService


def build_services(
    tmp_path: Path,
) -> tuple[CaseService, ReasoningService, ArgumentationService]:
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
    argumentation_repository = ArgumentationRepository(config.db_path)
    argumentation_repository.initialize()
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
        ReasoningService(
            reasoning_repository,
            mutation_backup=SQLiteMutationBackup(
                reasoning_repository.db_path,
                data_dir / "backups",
                keep=20,
            ),
        ),
        ArgumentationService(
            argumentation_repository,
            backup_dir=data_dir / "backups",
        ),
    )


def create_reasoned_case(
    tmp_path: Path,
) -> tuple[
    CaseService,
    ReasoningService,
    ArgumentationService,
    str,
    str,
    str,
]:
    case_service, reasoning_service, argumentation_service = build_services(
        tmp_path
    )
    case = case_service.create_case(
        CaseCreate(
            title="Caso argumental",
            description="Expediente sintético para validar Sprint 4.",
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
            question="¿Existe incumplimiento?",
            description="Problema jurídico sintético.",
            status=LegalIssueStatus.OPEN,
        )
    )
    reasoning_service.add_assertion(
        ReasoningAssertionCreate(
            case_id=case.id,
            issue_id=issue.id,
            predicate_key="premisa_confirmada",
            statement="La premisa relevante está confirmada.",
            value=AssertionValue.TRUE,
            basis="Valoración controlada para la prueba automatizada.",
            support_codes=[],
        )
    )
    reasoning_service.add_rule(
        ReasoningRuleCreate(
            case_id=case.id,
            issue_id=issue.id,
            name="Regla base argumental",
            kind=RuleKind.STRICT,
            conclusion_key="incumplimiento",
            conclusion_statement="Existe incumplimiento dentro del modelo.",
            conclusion_value=AssertionValue.TRUE,
            priority=100,
            active=True,
            legal_basis_codes=[],
            explanation="La premisa confirmada permite derivar la conclusión.",
            conditions=[
                RuleConditionCreate(
                    role=ConditionRole.PREREQUISITE,
                    predicate_key="premisa_confirmada",
                    expected_value=AssertionValue.TRUE,
                )
            ],
        )
    )
    report = reasoning_service.run(case_id=case.id, issue_id=issue.id)
    return (
        case_service,
        reasoning_service,
        argumentation_service,
        case.id,
        issue.id,
        report.conclusions[0].id,
    )


def create_manual_argument(
    service: ArgumentationService,
    *,
    case_id: str,
    issue_id: str,
    title: str,
    position: ArgumentPosition,
    value: AssertionValue,
) -> object:
    return service.add_argument(
        LegalArgumentCreate(
            case_id=case_id,
            issue_id=issue_id,
            title=title,
            position=position,
            thesis_key="incumplimiento",
            thesis_statement="Tesis manual sobre el incumplimiento.",
            thesis_value=value,
            claim="La pretensión argumental se formula de manera verificable.",
            reasoning=(
                "El razonamiento manual conecta la tesis con los elementos "
                "registrados en el expediente sintético."
            ),
            status=ArgumentStatus.DRAFT,
            fact_codes=[],
            evidence_codes=[],
            source_codes=[],
            rule_codes=[],
            assertion_codes=[],
        )
    )


def test_argument_is_created_from_reasoning_conclusion(tmp_path: Path) -> None:
    (
        _,
        _,
        argumentation_service,
        case_id,
        issue_id,
        conclusion_id,
    ) = create_reasoned_case(tmp_path)

    argument = argumentation_service.create_from_conclusion(
        conclusion_id=conclusion_id,
        position=ArgumentPosition.FAVORABLE,
        title="Argumento favorable sobre incumplimiento",
        claim="Debe reconocerse el incumplimiento dentro del modelo.",
        reasoning=(
            "La conclusión deriva de una premisa confirmada y de la regla "
            "estricta registrada."
        ),
        status=ArgumentStatus.VALIDATED,
    )

    assert argument.code == "ARG-001"
    assert argument.case_id == case_id
    assert argument.issue_id == issue_id
    assert argument.thesis_key == "incumplimiento"
    assert argument.thesis_value is AssertionValue.TRUE
    assert argument.rule_codes == ["R-001"]
    assert argument.assertion_codes == ["A-001"]


def test_invalid_support_code_is_rejected(tmp_path: Path) -> None:
    _, _, service, case_id, issue_id, _ = create_reasoned_case(tmp_path)

    with pytest.raises(ValueError, match="no existen"):
        service.add_argument(
            LegalArgumentCreate(
                case_id=case_id,
                issue_id=issue_id,
                title="Argumento con soporte inexistente",
                position=ArgumentPosition.FAVORABLE,
                thesis_key="incumplimiento",
                thesis_statement="Existe incumplimiento.",
                thesis_value=AssertionValue.TRUE,
                claim="La pretensión usa un hecho inexistente.",
                reasoning="La validación debe rechazar el código de soporte.",
                fact_codes=["H-999"],
                evidence_codes=[],
                source_codes=[],
                rule_codes=[],
                assertion_codes=[],
            )
        )


def test_attack_and_reply_update_unresolved_objections(tmp_path: Path) -> None:
    _, _, service, case_id, issue_id, conclusion_id = create_reasoned_case(
        tmp_path
    )
    favorable = service.create_from_conclusion(
        conclusion_id=conclusion_id,
        position=ArgumentPosition.FAVORABLE,
        title="Argumento favorable principal",
        claim="Debe reconocerse el incumplimiento.",
        reasoning="La conclusión se apoya en la inferencia trazada.",
    )
    adverse = create_manual_argument(
        service,
        case_id=case_id,
        issue_id=issue_id,
        title="Objeción adversa principal",
        position=ArgumentPosition.ADVERSE,
        value=AssertionValue.FALSE,
    )
    service.add_relation(
        ArgumentRelationCreate(
            case_id=case_id,
            issue_id=issue_id,
            source_argument_id=adverse.id,
            target_argument_id=favorable.id,
            relation_type=ArgumentRelationType.ATTACKS,
            rationale="La objeción cuestiona la suficiencia del soporte.",
        )
    )

    first = service.build_dossier(case_id, issue_id)
    assert first.unresolved_objection_codes == [adverse.code]
    assert first.summary["attack_count"] == 1

    service.add_relation(
        ArgumentRelationCreate(
            case_id=case_id,
            issue_id=issue_id,
            source_argument_id=favorable.id,
            target_argument_id=adverse.id,
            relation_type=ArgumentRelationType.REPLIES,
            rationale="La réplica explica la trazabilidad de la inferencia.",
        )
    )
    second = service.build_dossier(case_id, issue_id)
    assert second.unresolved_objection_codes == []


def test_cross_issue_relation_is_blocked(tmp_path: Path) -> None:
    case_service, _, service, case_id, issue_id, _ = create_reasoned_case(
        tmp_path
    )
    first = create_manual_argument(
        service,
        case_id=case_id,
        issue_id=issue_id,
        title="Argumento del primer problema",
        position=ArgumentPosition.FAVORABLE,
        value=AssertionValue.TRUE,
    )
    second_issue = case_service.add_legal_issue(
        LegalIssueCreate(
            case_id=case_id,
            title="Segundo problema",
            question="¿Existe otra consecuencia?",
            description="Problema separado para validar aislamiento.",
            status=LegalIssueStatus.OPEN,
        )
    )
    second = create_manual_argument(
        service,
        case_id=case_id,
        issue_id=second_issue.id,
        title="Argumento del segundo problema",
        position=ArgumentPosition.ADVERSE,
        value=AssertionValue.FALSE,
    )

    with pytest.raises(ArgumentationConflictError):
        service.add_relation(
            ArgumentRelationCreate(
                case_id=case_id,
                issue_id=issue_id,
                source_argument_id=first.id,
                target_argument_id=second.id,
                relation_type=ArgumentRelationType.ATTACKS,
                rationale="No debe cruzar problemas jurídicos.",
            )
        )


def test_exports_are_reproducible_and_docx_is_valid(tmp_path: Path) -> None:
    _, _, service, case_id, issue_id, conclusion_id = create_reasoned_case(
        tmp_path
    )
    service.create_from_conclusion(
        conclusion_id=conclusion_id,
        position=ArgumentPosition.FAVORABLE,
        title="Argumento exportable",
        claim="Debe reconocerse la conclusión inferida.",
        reasoning="El argumento conserva la trazabilidad del motor.",
    )

    first = service.build_dossier(case_id, issue_id)
    second = service.build_dossier(case_id, issue_id)
    assert first.input_hash == second.input_hash

    json_text = service.export_json(case_id, issue_id)
    assert json_text == service.export_json(case_id, issue_id)
    parsed = json.loads(json_text)
    assert parsed["dossier"]["input_hash"] == first.input_hash

    markdown = service.export_markdown(case_id, issue_id)
    assert "Informe de argumentación jurídica" in markdown
    assert "ARG-001" in markdown

    docx_bytes = service.export_docx(case_id, issue_id)
    assert docx_bytes.startswith(b"PK")
    assert len(docx_bytes) > 1000


def test_update_preserves_code_and_delete_requires_unlink(tmp_path: Path) -> None:
    _, _, service, case_id, issue_id, _ = create_reasoned_case(tmp_path)
    first = create_manual_argument(
        service,
        case_id=case_id,
        issue_id=issue_id,
        title="Argumento editable principal",
        position=ArgumentPosition.FAVORABLE,
        value=AssertionValue.TRUE,
    )
    second = create_manual_argument(
        service,
        case_id=case_id,
        issue_id=issue_id,
        title="Argumento relacionado adverso",
        position=ArgumentPosition.ADVERSE,
        value=AssertionValue.FALSE,
    )
    relation = service.add_relation(
        ArgumentRelationCreate(
            case_id=case_id,
            issue_id=issue_id,
            source_argument_id=second.id,
            target_argument_id=first.id,
            relation_type=ArgumentRelationType.ATTACKS,
            rationale="Relación temporal para probar eliminación segura.",
        )
    )

    updated = service.update_argument(
        first.id,
        LegalArgumentUpdate(
            title="Argumento principal actualizado",
            position=first.position,
            thesis_key=first.thesis_key,
            thesis_statement=first.thesis_statement,
            thesis_value=first.thesis_value,
            claim=first.claim,
            reasoning=first.reasoning,
            status=ArgumentStatus.VALIDATED,
            conclusion_id=first.conclusion_id,
            fact_codes=first.fact_codes,
            evidence_codes=first.evidence_codes,
            source_codes=first.source_codes,
            rule_codes=first.rule_codes,
            assertion_codes=first.assertion_codes,
        ),
    )
    assert updated.code == first.code
    assert updated.status is ArgumentStatus.VALIDATED

    with pytest.raises(ArgumentationConflictError):
        service.delete_argument(first.id, confirmation=first.code)

    service.delete_relation(relation.id, confirmation=relation.code)
    service.delete_argument(first.id, confirmation=first.code)
    remaining = service.list_arguments(case_id, issue_id)
    assert [item.code for item in remaining] == [second.code]

def test_support_diagnostic_reports_missing_components(tmp_path: Path) -> None:
    _, _, service, case_id, issue_id, conclusion_id = create_reasoned_case(
        tmp_path
    )
    argument = service.create_from_conclusion(
        conclusion_id=conclusion_id,
        position=ArgumentPosition.FAVORABLE,
        title="Argumento con trazabilidad parcial",
        claim="Debe reconocerse la conclusión inferida.",
        reasoning="La conclusión conserva regla y premisa, pero no prueba material.",
        status=ArgumentStatus.SUPPORTED,
    )

    dossier = service.build_dossier(case_id, issue_id)
    assessment = dossier.support_assessments[0]

    assert assessment.argument_code == argument.code
    assert assessment.level is ArgumentSupportLevel.LOW
    assert assessment.score == 2
    assert assessment.missing_components == [
        "hechos",
        "pruebas",
        "fuentes jurídicas",
    ]
    assert dossier.summary["missing_information_count"] == 1
    assert argument.code in dossier.missing_information[0]

def test_reasoning_support_from_other_issue_is_rejected(tmp_path: Path) -> None:
    (
        case_service,
        reasoning_service,
        service,
        case_id,
        issue_id,
        _,
    ) = create_reasoned_case(tmp_path)
    second_issue = case_service.add_legal_issue(
        LegalIssueCreate(
            case_id=case_id,
            title="Problema jurídico separado",
            question="¿Existe una obligación distinta?",
            description="Problema separado para validar los soportes.",
            status=LegalIssueStatus.OPEN,
        )
    )
    foreign_assertion = reasoning_service.add_assertion(
        ReasoningAssertionCreate(
            case_id=case_id,
            issue_id=second_issue.id,
            predicate_key="premisa_otro_problema",
            statement="La premisa pertenece a otro problema jurídico.",
            value=AssertionValue.TRUE,
            basis="Registro controlado para validar aislamiento.",
            support_codes=[],
        )
    )

    with pytest.raises(ValueError, match="no existen"):
        service.add_argument(
            LegalArgumentCreate(
                case_id=case_id,
                issue_id=issue_id,
                title="Argumento con premisa de otro problema",
                position=ArgumentPosition.FAVORABLE,
                thesis_key="incumplimiento",
                thesis_statement="Existe incumplimiento.",
                thesis_value=AssertionValue.TRUE,
                claim="La pretensión intenta usar una premisa ajena.",
                reasoning="El servicio debe preservar el aislamiento lógico.",
                assertion_codes=[foreign_assertion.code],
            )
        )

