from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from ius_razon.domain.enums import (
    JurisprudenceAuthority,
    LegalIssueStatus,
    LegalSourceType,
    NormHierarchy,
    SourceOrientation,
)
from ius_razon.domain.models import (
    CaseCreate,
    DoctrineCreate,
    IssueSourceLinkCreate,
    JurisprudenceCreate,
    LegalIssueCreate,
    NormCreate,
)
from ius_razon.persistence.sqlite_repository import ConflictError
from ius_razon.services.case_service import CaseService


def create_case(service: CaseService):
    return service.create_case(
        CaseCreate(
            title="Caso para corrección segura",
            description="Controversia contractual para validar edición y eliminación.",
            matter="Mercantil",
            jurisdiction="México",
        )
    )


def create_issue(service: CaseService, case_id: str):
    return service.add_legal_issue(
        LegalIssueCreate(
            case_id=case_id,
            title="Incumplimiento de entrega",
            question="¿La obligación de entrega era exigible en la fecha pactada?",
        )
    )


def create_norm(
    service: CaseService,
    case_id: str,
    *,
    with_file: bool = False,
):
    return service.add_norm(
        NormCreate(
            case_id=case_id,
            jurisdiction="México",
            matter="Mercantil",
            instrument="Código de demostración",
            article="Artículo 1",
            text="Las obligaciones deben cumplirse conforme a lo pactado.",
            hierarchy=NormHierarchy.FEDERAL_LAW,
            valid_from=date(2025, 1, 1),
        ),
        original_file_name="codigo.txt" if with_file else None,
        file_content=b"version inicial" if with_file else None,
    )


def link_issue_norm(
    service: CaseService,
    case_id: str,
    issue_id: str,
    norm_id: str,
) -> None:
    service.link_issue_source(
        IssueSourceLinkCreate(
            case_id=case_id,
            issue_id=issue_id,
            source_type=LegalSourceType.NORM,
            source_id=norm_id,
            orientation=SourceOrientation.SUPPORTS,
            applicability="Regula directamente el supuesto de incumplimiento.",
        )
    )


def test_update_preserves_codes_and_creates_backups(
    service: CaseService,
    tmp_path: Path,
) -> None:
    case = create_case(service)
    issue = create_issue(service, case.id)
    norm = create_norm(service, case.id)

    updated_issue = service.update_legal_issue(
        issue.id,
        LegalIssueCreate(
            case_id=case.id,
            title="Incumplimiento contractual de entrega",
            question="¿La falta de entrega constituye incumplimiento contractual exigible?",
            description="Pregunta corregida durante Sprint 2.1.",
            status=LegalIssueStatus.UNDER_ANALYSIS,
        ),
    )
    updated_norm = service.update_norm(
        norm.id,
        NormCreate(
            case_id=case.id,
            jurisdiction="México",
            matter="Mercantil",
            instrument="Código de demostración corregido",
            article="Artículo 1",
            text="Las obligaciones exigibles deben cumplirse en los términos pactados.",
            hierarchy=NormHierarchy.FEDERAL_LAW,
            valid_from=date(2025, 1, 1),
            notes="Corrección controlada.",
        ),
        original_file_name=None,
        file_content=None,
    )

    assert updated_issue.code == "PJ-001"
    assert updated_issue.status is LegalIssueStatus.UNDER_ANALYSIS
    assert updated_norm.code == "N-001"
    assert updated_norm.instrument.endswith("corregido")
    backups = list((tmp_path / "data" / "backups").glob("*.db"))
    assert len(backups) >= 2


def test_linked_source_and_issue_are_protected(service: CaseService) -> None:
    case = create_case(service)
    issue = create_issue(service, case.id)
    norm = create_norm(service, case.id)
    link_issue_norm(service, case.id, issue.id, norm.id)

    with pytest.raises(ConflictError, match="fuente"):
        service.delete_norm(
            norm_id=norm.id,
            case_id=case.id,
            confirmation_code=norm.code,
        )

    with pytest.raises(ConflictError, match="problema"):
        service.delete_legal_issue(
            issue_id=issue.id,
            case_id=case.id,
            confirmation_code=issue.code,
        )


def test_update_unlink_and_delete_flow(service: CaseService) -> None:
    case = create_case(service)
    issue = create_issue(service, case.id)
    norm = create_norm(service, case.id)
    link_issue_norm(service, case.id, issue.id, norm.id)

    service.update_issue_source_link(
        IssueSourceLinkCreate(
            case_id=case.id,
            issue_id=issue.id,
            source_type=LegalSourceType.NORM,
            source_id=norm.id,
            orientation=SourceOrientation.CONTEXTUAL,
            applicability="Aporta contexto sobre el contenido de la obligación.",
            notes="Texto corregido.",
        )
    )
    links = service.list_issue_source_links(case.id)
    assert len(links) == 1
    assert links[0].orientation is SourceOrientation.CONTEXTUAL
    assert links[0].notes == "Texto corregido."

    service.unlink_issue_source(
        case_id=case.id,
        issue_id=issue.id,
        source_type=LegalSourceType.NORM,
        source_id=norm.id,
        confirmation_code=norm.code,
    )
    assert service.list_issue_source_links(case.id) == []

    service.delete_norm(
        norm_id=norm.id,
        case_id=case.id,
        confirmation_code=norm.code,
    )
    service.delete_legal_issue(
        issue_id=issue.id,
        case_id=case.id,
        confirmation_code=issue.code,
    )
    summary = service.get_case_summary(case.id)
    assert summary.norm_count == 0
    assert summary.legal_issue_count == 0


def test_wrong_confirmation_cancels_delete(service: CaseService) -> None:
    case = create_case(service)
    norm = create_norm(service, case.id)

    with pytest.raises(ValueError, match="exactamente"):
        service.delete_norm(
            norm_id=norm.id,
            case_id=case.id,
            confirmation_code="N-999",
        )

    assert service.list_norms(case.id)[0].code == norm.code


def test_replacing_source_file_removes_previous_file(
    service: CaseService,
    tmp_path: Path,
) -> None:
    case = create_case(service)
    norm = create_norm(service, case.id, with_file=True)
    old_path = tmp_path / "data" / "uploads" / case.id / str(norm.stored_file_name)
    assert old_path.is_file()

    updated = service.update_norm(
        norm.id,
        NormCreate(
            case_id=case.id,
            jurisdiction="México",
            matter="Mercantil",
            instrument=norm.instrument,
            article=norm.article,
            text=norm.text,
            hierarchy=norm.hierarchy,
        ),
        original_file_name="codigo_nuevo.txt",
        file_content=b"version reemplazada",
    )

    new_path = tmp_path / "data" / "uploads" / case.id / str(updated.stored_file_name)
    archived_path = (
        tmp_path
        / "data"
        / "archived_uploads"
        / case.id
        / str(norm.stored_file_name)
    )
    assert not old_path.exists()
    assert archived_path.is_file()
    assert new_path.is_file()
    assert updated.file_sha256 != norm.file_sha256


def test_audit_registers_corrections_and_deletions(service: CaseService) -> None:
    case = create_case(service)
    issue = create_issue(service, case.id)

    service.update_legal_issue(
        issue.id,
        LegalIssueCreate(
            case_id=case.id,
            title=issue.title,
            question="¿La obligación fue incumplida después del vencimiento pactado?",
            status=LegalIssueStatus.UNDER_ANALYSIS,
        ),
    )
    service.delete_legal_issue(
        issue_id=issue.id,
        case_id=case.id,
        confirmation_code=issue.code,
    )

    event_types = {event.event_type for event in service.list_audit_events(case.id)}
    assert "legal_issue.updated" in event_types
    assert "legal_issue.deleted" in event_types


def test_update_and_delete_jurisprudence_and_doctrine(
    service: CaseService,
) -> None:
    case = create_case(service)
    precedent = service.add_jurisprudence(
        JurisprudenceCreate(
            case_id=case.id,
            court="Tribunal de prueba",
            identifier="REG-001",
            jurisdiction="México",
            matter="Mercantil",
            relevant_facts="La entrega no ocurrió después del pago pactado.",
            legal_question="¿La falta de entrega genera incumplimiento?",
            criterion="La exigibilidad depende del vencimiento de la obligación.",
            authority=JurisprudenceAuthority.PENDING_VERIFICATION,
        ),
        original_file_name=None,
        file_content=None,
    )
    doctrine = service.add_doctrine(
        DoctrineCreate(
            case_id=case.id,
            author="Autora inicial",
            work_title="Obligaciones de prueba",
            concept="Incumplimiento",
            position_summary="La obligación debe ser válida, exigible y vencida.",
            citation="Autora inicial. (2025). Obligaciones de prueba.",
        ),
        original_file_name=None,
        file_content=None,
    )

    updated_precedent = service.update_jurisprudence(
        precedent.id,
        JurisprudenceCreate(
            case_id=case.id,
            court="Tribunal de prueba corregido",
            identifier="REG-001-C",
            jurisdiction="México",
            matter="Mercantil",
            relevant_facts=precedent.relevant_facts,
            legal_question=precedent.legal_question,
            criterion="La obligación debe ser exigible y no estar justificada.",
            authority=JurisprudenceAuthority.ORIENTATIVE,
        ),
        original_file_name=None,
        file_content=None,
    )
    updated_doctrine = service.update_doctrine(
        doctrine.id,
        DoctrineCreate(
            case_id=case.id,
            author="Autora corregida",
            work_title=doctrine.work_title,
            concept=doctrine.concept,
            position_summary="La corrección distingue obligación y excepción.",
            citation="Autora corregida. (2026). Obligaciones de prueba.",
        ),
        original_file_name=None,
        file_content=None,
    )

    assert updated_precedent.code == "J-001"
    assert updated_precedent.authority is JurisprudenceAuthority.ORIENTATIVE
    assert updated_doctrine.code == "D-001"
    assert updated_doctrine.author == "Autora corregida"

    service.delete_jurisprudence(
        jurisprudence_id=precedent.id,
        case_id=case.id,
        confirmation_code=precedent.code,
    )
    service.delete_doctrine(
        doctrine_id=doctrine.id,
        case_id=case.id,
        confirmation_code=doctrine.code,
    )

    summary = service.get_case_summary(case.id)
    assert summary.jurisprudence_count == 0
    assert summary.doctrine_count == 0


def test_deleted_codes_are_not_reused(service: CaseService) -> None:
    case = create_case(service)
    first = create_norm(service, case.id)
    second = service.add_norm(
        NormCreate(
            case_id=case.id,
            jurisdiction="México",
            matter="Mercantil",
            instrument="Segundo código",
            article="Artículo 2",
            text="Texto suficiente para el segundo registro normativo.",
        ),
        original_file_name=None,
        file_content=None,
    )
    assert (first.code, second.code) == ("N-001", "N-002")

    service.delete_norm(
        norm_id=second.id,
        case_id=case.id,
        confirmation_code=second.code,
    )
    third = service.add_norm(
        NormCreate(
            case_id=case.id,
            jurisdiction="México",
            matter="Mercantil",
            instrument="Tercer código",
            article="Artículo 3",
            text="Texto suficiente para comprobar que el código no se reutiliza.",
        ),
        original_file_name=None,
        file_content=None,
    )

    assert third.code == "N-003"
